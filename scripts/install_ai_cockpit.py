#!/usr/bin/env python3
"""Install AI Cockpit into an existing repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, cast

from ai_generate_status import write_no_active_status
from ai_adoption_evidence import build_runtime_verification
from ai_upgrade_conflict_report import build_report
from ai_preflight_review import upgrade_conflict_gate
from ai_start_receipt import build_receipt, receipt_binding
from ai_install_facts import FACT_NAMES, write_fact_bundle
from ai_installer_bootstrap import adoption_record_paths
from ai_installer_detection import missing_runtime_scripts
from ai_installer_detection import InstallationDetection, collect_installation_detection
from ai_installer_evidence import action_counts
from ai_installer_ownership import is_project_owned
from ai_installer_repository import clean_git_environment, git_records, git_target_args, run_git
from ai_installer_transaction import TransactionAction
from ai_installer_upgrade import release_semver as installer_release_semver

CATALOG_NAME = "ai_installer_catalog.json"
CATALOG_PATH = Path(__file__).with_name(CATALOG_NAME)
_CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
STACKS = frozenset(_CATALOG["stacks"])
SCRIPT_NAMES = frozenset(_CATALOG["scripts"])
RUNTIME_TARGETS = (
    "ai-cockpit-version",
    "ai-lifecycle-facts",
    "ai-cockpit-update-check",
    "ai-cockpit-update-propose",
    "ai-cockpit-update-apply",
    "ai-cockpit-rollback-propose",
    "ai-cockpit-disable",
    "ai-cockpit-enable",
    "ai-cockpit-uninstall-propose",
)

RUNTIME_SURFACE_SCRIPTS = frozenset(
    {
        "ai_install_status.py",
        "ai_lifecycle_facts.py",
        "ai_upgrade_proposal.py",
        "ai_upgrade_apply.py",
        "ai_rollback.py",
        "ai_disable_enable.py",
        "ai_uninstall_proposal.py",
    }
)
AGENT_MARKER = "<!-- AI_COCKPIT_SECTION -->"
AGENT_END_MARKER = "<!-- /AI_COCKPIT_SECTION -->"
GITIGNORE_MARKER = "# AI Cockpit local state"
GITIGNORE_SECTION = """# AI Cockpit local state
.ai/work-items/active/*.contract.json
.ai/work-items/active/*.summary.json
.ai/work-items/active/*.review.json
.ai/cockpit/upgrade-backups/
.ai/project_profile.proposed.yaml
target/ai_*.json
target/ai_*.jsonl
"""
GITIGNORE_RULES = tuple(
    line for line in GITIGNORE_SECTION.splitlines() if line and not line.startswith("#")
)
COMMON_TRACKED_HYGIENE_NAMES = frozenset({".DS_Store", "Thumbs.db"})
COMMON_TRACKED_HYGIENE_SUFFIXES = (".xcuserstate",)
TEMPLATE_SUPPLY_CHAIN_BASELINES = frozenset(
    {
        ("cockpit", "bandit_low_risk_baseline.json"),
        ("cockpit", "provenance.json"),
        ("cockpit", "release-digests.json"),
        ("cockpit", "sbom.json"),
    }
)
RESERVED_MAKE_TARGETS = {
    "ai-cockpit-project-format-check",
    "ai-cockpit-project-test",
    "ai-cockpit-project-lint",
    "ai-cockpit-diff-check",
    "ai-cockpit-quality",
}


Action = TransactionAction


def inspect_installation(
    target: Path, *, mode: str, stacks: Iterable[str] = ()
) -> InstallationDetection:
    """Expose the read-only wizard facts without entering the Installer transaction."""
    return collect_installation_detection(target, mode=mode, stacks=stacks)


@dataclass(frozen=True)
class GitHeadSnapshot:
    """採用前の HEAD 状態。ブランチまたは detached HEAD を保持する。"""

    commit: str
    branch: str | None

    @property
    def detached(self) -> bool:
        return self.branch is None


def adoption_preflight_warnings(target: Path) -> list[str]:
    """--create-adoption 失敗前に dirty worktree と tracked 衛生ファイルを警告する。"""
    warnings: list[str] = []
    git_args = git_target_args(target)
    git_env = clean_git_environment()
    status = subprocess.run(
        ["git", *git_args, "status", "--porcelain", "-z"],
        cwd=target,
        text=True,
        capture_output=True,
        check=False,
        env=git_env,
    )
    if status.returncode == 0 and status.stdout.strip():
        dirty_lines = [line.rstrip() for line in git_records(status.stdout)]
        preview = ", ".join(dirty_lines[:5])
        if len(dirty_lines) > 5:
            preview = f"{preview} (+{len(dirty_lines) - 5} more)"
        warnings.append(
            "Git worktree is not clean "
            f"({preview}); --create-adoption requires a clean worktree before installation."
        )
    ls_files = subprocess.run(
        ["git", *git_args, "ls-files", "-z"],
        cwd=target,
        text=True,
        capture_output=True,
        check=False,
        env=git_env,
    )
    if ls_files.returncode == 0:
        tracked_hygiene = []
        for path in [item for item in ls_files.stdout.split("\0") if item]:
            name = Path(path).name
            if name in COMMON_TRACKED_HYGIENE_NAMES or name.endswith(
                COMMON_TRACKED_HYGIENE_SUFFIXES
            ):
                tracked_hygiene.append(path)
        if tracked_hygiene:
            preview = ", ".join(tracked_hygiene[:5])
            if len(tracked_hygiene) > 5:
                preview = f"{preview} (+{len(tracked_hygiene) - 5} more)"
            warnings.append(
                "Tracked files commonly ignored locally "
                f"({preview}); remove or untrack them before adoption to avoid noisy diffs."
            )
    return warnings


class Installer:
    def __init__(
        self,
        *,
        source: Path,
        target: Path,
        stack: str,
        force: bool,
        dry_run: bool,
        with_examples: bool,
        update_makefile: bool,
        upgrade: bool = False,
        upgrade_with_active: bool = False,
        replace_glossary: bool = False,
        create_adoption: bool = False,
        base_remote: str | None = None,
        base_branch: str | None = None,
        confirm_upgrade_conflicts: bool = False,
    ) -> None:
        self.source = source.resolve()
        self.target = target.resolve()
        self.stack = stack
        self.force = force
        self.dry_run = dry_run
        self.with_examples = with_examples
        self.update_makefile = update_makefile
        self.upgrade = upgrade
        self.upgrade_with_active = upgrade_with_active
        self.replace_glossary = replace_glossary
        self.create_adoption = create_adoption
        self.base_remote = base_remote
        self.base_branch = base_branch
        self.confirm_upgrade_conflicts = confirm_upgrade_conflicts
        self.backup_dir = (
            self.target
            / ".ai"
            / "cockpit"
            / "upgrade-backups"
            / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        )
        self.actions: list[Action] = []
        self.backups: dict[Path, Path] = {}
        self.created_paths: set[Path] = set()
        self.preexisting_dirs: set[Path] = set()
        self.created_adoption_branch: str | None = None
        self.original_git_head: GitHeadSnapshot | None = None
        self.upgrade_conflicts: list[dict[str, str]] = []
        self.upgrade_conflict_report: dict[str, object] | None = None

    def install(self) -> int:
        if not self.source.exists():
            print(f"ERROR: source template does not exist: {self.source}", file=sys.stderr)
            return 2
        if self.stack not in STACKS:
            print(
                f"ERROR: unsupported stack {self.stack}; expected one of {sorted(STACKS)}",
                file=sys.stderr,
            )
            return 2
        if self.upgrade and not self.upgrade_preflight():
            return 2
        if self.create_adoption and not self.adoption_preflight():
            return 2
        available_runtime = {
            name
            for name in RUNTIME_SURFACE_SCRIPTS
            if name in SCRIPT_NAMES and (self.source / "scripts" / name).is_file()
        }
        missing_runtime = missing_runtime_scripts(set(RUNTIME_SURFACE_SCRIPTS), available_runtime)
        if missing_runtime:
            print(
                "ERROR: required installed runtime scripts are unavailable: "
                + ", ".join(missing_runtime),
                file=sys.stderr,
            )
            return 2
        # ブランチ変更の前に marker / managed-conflict 検証を完了する。
        try:
            self.validate_agent_markers()
            self.validate_managed_conflicts()
        except (OSError, ValueError) as exc:
            print(f"ERROR: installation failed before writing: {exc}", file=sys.stderr)
            return 2
        if self.create_adoption and not self.prepare_adoption_branch():
            return 2
        if self.upgrade and not self.prepare_upgrade_branch():
            return 2
        if self.target.exists():
            self.preexisting_dirs = {
                self.target,
                *(path for path in self.target.rglob("*") if path.is_dir()),
            }
        self.target.mkdir(parents=True, exist_ok=True)
        try:
            if self.create_adoption:
                self.create_adoption_records()
            if self.upgrade:
                self.create_upgrade_records()
            self.copy_tree(".ai")
            self.copy_tree(".cursor")
            self.copy_scripts()
            self.copy_file("templates/make/Makefile.ai", "Makefile.ai")
            self.copy_file(f"templates/stacks/{self.stack}.mk", "Makefile.ai.stack")
            self.install_glossary()
            if self.with_examples:
                self.copy_tree("examples")
            self.install_agent_doc("AGENTS.md")
            self.install_agent_doc("GEMINI.md")
            self.install_agent_doc("CLAUDE.md")
            self.install_gitignore()
            if self.update_makefile:
                self.append_makefile_include()
            self.install_initial_status()
            self.install_lifecycle_facts()
            self.validate_managed_installation()
            if self.create_adoption:
                self.finalize_adoption_records()
            if self.upgrade:
                self.finalize_upgrade_records()
        except (
            OSError,
            json.JSONDecodeError,
            ValueError,
            RuntimeError,
            subprocess.SubprocessError,
        ) as exc:
            if not self.dry_run:
                self.rollback_installation()
                if self.upgrade_conflict_report is not None:
                    report_path = self.target / ".ai" / "cockpit" / "upgrade-conflict-report.json"
                    report_path.parent.mkdir(parents=True, exist_ok=True)
                    report_path.write_text(
                        json.dumps(self.upgrade_conflict_report, indent=2) + "\n",
                        encoding="utf-8",
                    )
            print(f"ERROR: installation failed: {exc}", file=sys.stderr)
            return 2

        self.print_summary()
        return 0

    def validate_agent_markers(self) -> None:
        for name in ("AGENTS.md", "GEMINI.md", "CLAUDE.md"):
            path = self.target / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            starts = text.count(AGENT_MARKER)
            ends = text.count(AGENT_END_MARKER)
            if starts == 0 and ends == 0:
                continue
            if starts != 1 or ends != 1:
                raise ValueError(
                    f"{name}: malformed AI Cockpit markers; expected exactly one start and one end marker"
                )
            if text.index(AGENT_MARKER) > text.index(AGENT_END_MARKER):
                raise ValueError(
                    f"{name}: malformed AI Cockpit markers; end marker appears before start marker"
                )

    def tree_copy_pairs(self, relative: str) -> list[tuple[Path, Path]]:
        src = self.source / relative
        dst = self.target / relative
        if not src.exists():
            return []
        pairs: list[tuple[Path, Path]] = []
        for item in src.rglob("*"):
            if item.is_dir():
                continue
            rel = item.relative_to(src)
            if relative == ".ai" and rel.as_posix() in {
                "cockpit/current_status.md",
                "glossary.md",
                "project_profile.yaml",
                "project_profile.proposed.yaml",
            }:
                continue
            if (
                relative == ".ai"
                and len(rel.parts) >= 3
                and rel.parts[:2] == ("work-items", "active")
                and rel.name != ".gitkeep"
            ):
                continue
            if (
                relative == ".ai"
                and len(rel.parts) >= 3
                and rel.parts[:2] == ("work-items", "archive")
                and rel.name != ".gitkeep"
            ):
                continue
            if (
                relative == ".ai"
                and len(rel.parts) >= 2
                and rel.parts[:2] in TEMPLATE_SUPPLY_CHAIN_BASELINES
            ):
                continue
            pairs.append((item, dst / rel))
        return pairs

    def managed_copy_pairs(self) -> list[tuple[Path, Path]]:
        pairs = [*self.tree_copy_pairs(".ai"), *self.tree_copy_pairs(".cursor")]
        pairs.extend(
            (self.source / "scripts" / name, self.target / "scripts" / name)
            for name in sorted(SCRIPT_NAMES)
        )
        pairs.append(
            (self.source / "scripts" / CATALOG_NAME, self.target / "scripts" / CATALOG_NAME)
        )
        pairs.append(
            (self.source / "templates" / "make" / "Makefile.ai", self.target / "Makefile.ai")
        )
        if self.with_examples:
            pairs.extend(self.tree_copy_pairs("examples"))
        return pairs

    def validate_managed_conflicts(self) -> None:
        self.validate_make_target_conflicts()
        if self.force or self.upgrade:
            return
        pairs = self.managed_copy_pairs()
        if not (self.target / ".ai" / "cockpit" / "version.json").exists():
            pairs.append(
                (
                    self.source / "templates" / "stacks" / f"{self.stack}.mk",
                    self.target / "Makefile.ai.stack",
                )
            )
        conflicts = []
        for src, dst in pairs:
            if not dst.exists():
                continue
            if not dst.is_file() or src.read_bytes() != dst.read_bytes():
                conflicts.append(dst.relative_to(self.target).as_posix())
        if conflicts:
            formatted = "\n  - ".join(sorted(conflicts))
            raise ValueError(
                "managed file conflicts detected; move the files, use --force for intentional replacement, "
                f"or use --upgrade for an existing installation:\n  - {formatted}"
            )

    def validate_make_target_conflicts(self) -> None:
        makefile = self.target / "Makefile"
        if not self.update_makefile or not makefile.is_file():
            return
        defined: set[str] = set()
        for line in makefile.read_text(encoding="utf-8").splitlines():
            if not line or line[0].isspace() or line.lstrip().startswith("#"):
                continue
            match = re.match(r"^([^:=]+):(?!=)", line)
            if match:
                defined.update(token for token in match.group(1).split() if token)
        conflicts = sorted(defined & RESERVED_MAKE_TARGETS)
        if conflicts:
            raise ValueError(
                "host Makefile defines reserved AI Cockpit target(s): "
                + ", ".join(conflicts)
                + "; rename the host target or install without --update-makefile"
            )

    def validate_managed_installation(self) -> None:
        if self.dry_run:
            return
        source_version = self.load_version(self.source / ".ai" / "cockpit" / "version.json")
        installed_version = self.load_version(self.target / ".ai" / "cockpit" / "version.json")
        if installed_version != source_version:
            raise ValueError("installed version metadata does not match the source distribution")
        invalid = []
        preserved = {item["path"] for item in self.upgrade_conflicts}
        for src, dst in self.managed_copy_pairs():
            if not dst.is_file() or src.read_bytes() != dst.read_bytes():
                relative = dst.relative_to(self.target).as_posix()
                if relative not in preserved:
                    invalid.append(relative)
        stack = self.target / "Makefile.ai.stack"
        if not stack.is_file():
            invalid.append("Makefile.ai.stack")
        if invalid:
            raise ValueError(
                f"installed managed files are missing or inconsistent: {', '.join(sorted(invalid))}"
            )

        modules = ", ".join(
            path.stem
            for path in sorted((self.target / "scripts").glob("ai_*.py"))
            if path.name in SCRIPT_NAMES
        )
        import_result = subprocess.run(
            [sys.executable, "-c", f"import {modules}"],
            cwd=self.target,
            text=True,
            capture_output=True,
            check=False,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(self.target / "scripts"),
            },
        )
        if import_result.returncode != 0:
            raise ValueError(
                f"installed Python runtime import failed: {import_result.stderr.strip()}"
            )

        make_result = subprocess.run(
            ["make", "-f", "Makefile.ai", "-n", "ai-help"],
            cwd=self.target,
            text=True,
            capture_output=True,
            check=False,
        )
        if make_result.returncode != 0:
            raise ValueError(
                f"installed Makefile.ai validation failed: {make_result.stderr.strip()}"
            )
        make_targets = {
            match.group(1)
            for line in (self.target / "Makefile.ai").read_text(encoding="utf-8").splitlines()
            if (match := re.match(r"^([^:=\s]+):(?!=)", line))
        }
        missing_targets = sorted(set(RUNTIME_TARGETS) - make_targets)
        if missing_targets:
            raise ValueError(
                "installed Makefile.ai is missing Runtime Surface target(s): "
                + ", ".join(missing_targets)
            )

    def capture_git_head(self) -> GitHeadSnapshot | None:
        """現在の HEAD をブランチ名または detached commit として記録する。"""
        commit = run_git(self.target, ["rev-parse", "--verify", "HEAD"])
        if commit.returncode != 0:
            return None
        branch = run_git(self.target, ["symbolic-ref", "--quiet", "--short", "HEAD"])
        if branch.returncode == 0 and branch.stdout.strip():
            return GitHeadSnapshot(commit=commit.stdout.strip(), branch=branch.stdout.strip())
        return GitHeadSnapshot(commit=commit.stdout.strip(), branch=None)

    def restore_git_head(self, snapshot: GitHeadSnapshot) -> bool:
        """記録した HEAD 状態へ非破壊的に戻す（reset は使わない）。"""
        if snapshot.detached:
            restored = run_git(self.target, ["switch", "--detach", snapshot.commit])
        else:
            branch = snapshot.branch
            if not branch:
                print(
                    "ERROR: original Git HEAD snapshot is missing a branch name.",
                    file=sys.stderr,
                )
                return False
            restored = run_git(self.target, ["switch", branch])
        if restored.returncode != 0:
            print(
                f"ERROR: failed to restore original Git HEAD: {restored.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        return True

    def rollback_installation(self) -> None:
        created = self.created_adoption_branch
        if created and self.original_git_head is not None:
            # 作成ブランチ上にいる場合は先に元 HEAD へ戻してから削除する。
            if self.restore_git_head(self.original_git_head):
                deleted = run_git(self.target, ["branch", "-D", created])
                if deleted.returncode != 0:
                    print(
                        f"ERROR: failed to delete adoption branch {created}: "
                        f"{deleted.stderr.strip()}",
                        file=sys.stderr,
                    )
                else:
                    self.created_adoption_branch = None
            else:
                print(
                    "ERROR: adoption branch was left in place because original HEAD "
                    "could not be restored.",
                    file=sys.stderr,
                )
        for original, backup in reversed(list(self.backups.items())):
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, original)
        for path in sorted(self.created_paths, key=lambda item: len(item.parts), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
        shutil.rmtree(self.backup_dir, ignore_errors=True)
        candidate_dirs = {
            parent
            for path in [*self.created_paths, self.backup_dir]
            for parent in path.parents
            if parent != self.target
            and self.target in parent.parents
            and parent not in self.preexisting_dirs
        }
        for directory in sorted(candidate_dirs, key=lambda item: len(item.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        print("Installation transaction rolled back")

    def adoption_preflight(self) -> bool:
        if self.upgrade:
            print(
                "ERROR: --create-adoption is for first installation and cannot be combined with --upgrade.",
                file=sys.stderr,
            )
            return False
        for warning in adoption_preflight_warnings(self.target):
            print(f"WARN: {warning}", file=sys.stderr)
        # --git-dir を明示することで、CI 環境での git 自動発見が親リポジトリを誤って使うことを防ぐ。
        git_args = git_target_args(self.target)
        head = subprocess.run(
            ["git", *git_args, "rev-parse", "--verify", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        )
        if head.returncode != 0:
            print(
                "ERROR: --create-adoption requires a Git repository with at least one commit.",
                file=sys.stderr,
            )
            return False
        status = subprocess.run(
            ["git", *git_args, "status", "--porcelain", "-z"],
            cwd=self.target,
            text=True,
            capture_output=True,
            check=False,
        )
        if status.returncode != 0 or any(git_records(status.stdout)):
            print(
                "ERROR: --create-adoption requires a clean Git worktree before installation.",
                file=sys.stderr,
            )
            return False
        active = self.target / ".ai" / "work-items" / "active"
        if active.exists() and any(active.glob("*.json")):
            print(
                "ERROR: --create-adoption requires no existing active Work Item.", file=sys.stderr
            )
            return False
        return True

    def adoption_paths(self) -> tuple[Path, Path]:
        return adoption_record_paths(self.target)

    def prepare_adoption_branch(self) -> bool:
        """最新の remote default branch から採用ブランチを作成する。

        dry-run では fetch / ブランチ作成 / switch / 削除を行わない。
        """
        remote, branch = self.adopter_git_context()
        if not remote or not branch:
            print(
                "WARN: --create-adoption could not discover a remote default branch; "
                "continuing without branch creation for local-only repositories.",
                file=sys.stderr,
            )
            return True
        branch_name = os.environ.get("AI_COCKPIT_ADOPTION_BRANCH", "adopt/ai-cockpit")
        if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch_name) or branch_name.startswith("/"):
            print("ERROR: AI_COCKPIT_ADOPTION_BRANCH is not a valid branch name.", file=sys.stderr)
            return False
        if self.dry_run:
            print(
                f"DRY-RUN: would create adoption branch {branch_name} from {remote}/{branch} "
                "(no fetch, branch creation, switch, or deletion)"
            )
            return True
        self.original_git_head = self.capture_git_head()
        if self.original_git_head is None:
            print("ERROR: failed to capture original Git HEAD before adoption.", file=sys.stderr)
            return False
        target_args = git_target_args(self.target)
        for args, message in (
            (["fetch", remote, branch], "fetch adopter default branch"),
            (
                ["show-ref", "--verify", f"refs/remotes/{remote}/{branch}"],
                "verify remote default branch",
            ),
        ):
            result = subprocess.run(
                ["git", *target_args, *args],
                cwd=self.target,
                text=True,
                capture_output=True,
                check=False,
                env=clean_git_environment(),
            )
            if result.returncode != 0:
                print(f"ERROR: failed to {message}: {result.stderr.strip()}", file=sys.stderr)
                return False
        existing = run_git(self.target, ["show-ref", "--verify", f"refs/heads/{branch_name}"])
        if existing.returncode == 0:
            print(f"ERROR: adoption branch already exists: {branch_name}", file=sys.stderr)
            return False
        created = run_git(self.target, ["switch", "--create", branch_name, f"{remote}/{branch}"])
        if created.returncode != 0:
            print(
                f"ERROR: failed to create adoption branch: {created.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        self.created_adoption_branch = branch_name
        print(f"Created adoption branch {branch_name} from {remote}/{branch}")
        return True

    @staticmethod
    def write_json(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def adopter_git_context(self) -> tuple[str | None, str | None]:
        remotes = run_git(self.target, ["remote"])
        if remotes.returncode != 0:
            return None, None
        for remote in remotes.stdout.splitlines():
            remote = remote.strip()
            if not remote:
                continue
            head = run_git(
                self.target, ["symbolic-ref", "--quiet", "--short", f"refs/remotes/{remote}/HEAD"]
            )
            ref = head.stdout.strip()
            if head.returncode == 0 and ref.startswith(f"{remote}/"):
                return remote, ref.removeprefix(f"{remote}/")
        return None, None

    def source_context(self) -> tuple[str, str]:
        release_path = self.source / "release.json"
        release_tag = os.environ.get("AI_COCKPIT_TEMPLATE_REF", "")
        if not release_tag and release_path.is_file():
            try:
                release_tag = str(
                    json.loads(release_path.read_text(encoding="utf-8")).get("releaseTag", "")
                )
            except (OSError, json.JSONDecodeError):
                pass
        source_repository = os.environ.get("AI_COCKPIT_TEMPLATE_REPO", "local source")
        return release_tag or "unknown release reference", source_repository

    def create_adoption_records(self) -> None:
        contract_path, summary_path = self.adoption_paths()
        # Target worktree を明示する。--git-dir だけでは worktree 情報が
        # 欠け、親リポジトリや CI の Git metadata を参照し得る。
        base_commit = subprocess.run(
            ["git", *git_target_args(self.target), "rev-parse", "--verify", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
            cwd=self.target,
            env=clean_git_environment(),
        ).stdout.strip()
        base_remote, base_branch = self.adopter_git_context()
        source_release_tag, source_repository = self.source_context()
        contract_rel = contract_path.relative_to(self.target).as_posix()
        verification = [
            {"check": check, "required": True}
            for check in (
                "aiWorkItem",
                "aiScope",
                "aiAgentRisk",
                "aiSummary",
                "aiStatus",
                "aiStatusCheck",
            )
        ]
        adoption_guidelines = ["Do not claim project quality checks are configured by adoption."]
        archive_growth = (
            len(list((self.target / ".ai" / "work-items" / "archive").rglob("*.contract.json"))) + 1
        )
        contract = {
            "contractVersion": 2,
            "workItemId": "adopt_ai_cockpit",
            "mode": "code",
            "title": "Adopt AI Cockpit governance",
            "baseCommit": base_commit,
            **dict(
                zip(
                    ("baseRemote", "baseBranch", "sourceReleaseTag", "sourceRepository"),
                    (base_remote, base_branch, source_release_tag, source_repository),
                )
            ),
            "baselineDirtyPaths": [],
            "adoptionBootstrapPaths": ["scripts/ai_*.py"],
            "scope": [
                ".ai/**",
                ".ai/work-items/starts/**",
                ".cursor/**",
                "scripts/ai_*.py",
                "scripts/ai_installer_catalog.json",
                "scripts/bootstrap_*.py",
                "Makefile.ai",
                "Makefile.ai.stack",
                "AGENTS.md",
                "GEMINI.md",
                "CLAUDE.md",
                ".gitignore",
                "Makefile",
                "examples/**",
            ],
            "outOfScope": [
                "Product source changes",
                "Claiming project-specific quality checks are configured",
            ],
            "sources": [
                {
                    "path": ".ai/cockpit/adoption.md",
                    "reason": "Installed first-adoption and production-readiness workflow.",
                },
                {
                    "path": "installer action log",
                    "reason": "Records the files and source identity written during adoption.",
                },
            ],
            "intent": {
                "problem": "The adopter repository needs an auditable AI Cockpit governance baseline before product Work Items begin.",
                "constraints": [
                    "Record installation and governance files only; do not claim project quality checks are configured.",
                    "Use the adopter repository's discovered base commit and remote context.",
                ],
                "rationale": "A structured adoption Contract must itself be ready under the enforced Preflight profile so the first governance PR can be verified without bypassing the Trust Gate.",
            },
            "problemStatement": "Install the AI Cockpit governance baseline and record the adopter-specific source identity and ownership evidence.",
            "scenarioCoverage": [
                {
                    "scenario": "Fresh adoption Contract has sufficient intent and evidence for enforced Preflight.",
                    "required": True,
                    "status": "verified",
                    "evidence": ["installer action log", ".ai/cockpit/adoption.md"],
                },
                {
                    "scenario": "Project quality remains explicitly unconfigured after adoption.",
                    "required": True,
                    "status": "verified",
                    "evidence": ["adoption Contract outOfScope", "adoption guideline"],
                },
            ],
            "unknowns": [],
            "notCodable": False,
            "riskAssessment": {
                "level": "low",
                "riskTypes": ["governance_bootstrap"],
                "reason": "The first governance PR is bounded to installer-created governance files and has explicit adoption evidence.",
            },
            "agentCapability": {
                "canImplement": True,
                "canVerify": True,
                "needsHumanDecision": False,
                "blockedReason": "",
            },
            "executionDecision": {
                "status": "continue",
                "reason": "The installer records the complete clean-worktree adoption diff.",
            },
            "preReviewWarnings": [
                "Protected platform review remains required for trusted approval."
            ],
            "checkpointPolicy": {
                "requiredBeforeFinish": False,
                "requiredStages": [],
                "reason": "Installer-generated bounded adoption record.",
            },
            "acceptance": [
                "All installer-created changes are owned by this Contract and Summary.",
                "The archived pair passes check-ai-pr for the complete adoption diff.",
            ],
            "guidelines": adoption_guidelines,
            "verification": verification,
            "destructiveChangePolicy": {
                "allowed": False,
                "requiresHumanApproval": True,
                "allowPatterns": [],
            },
            "restrictedWriteApproval": {
                "approved": True,
                "approvedBy": "installer adoption workflow",
                "reason": "The user explicitly invoked --create-adoption to introduce governance files.",
            },
            "rollbackNote": "Revert the adoption commit to remove AI Cockpit governance files.",
            "budgetImpact": {"expectedMetrics": {"archiveGrowth": archive_growth}},
        }
        receipt = build_receipt(contract, project_root=self.target)
        contract["startReceipt"] = receipt_binding(receipt)
        receipt_path = self.target / receipt["receiptPath"]
        summary = {
            "summaryVersion": 2,
            "workItemId": "adopt_ai_cockpit",
            "contractPath": contract_rel,
            "changedFiles": [],
            "sourcesUsed": [
                ".ai/cockpit/adoption.md",
                "installer action log",
                "adopter repository Git remote HEAD",
                "release.json or AI_COCKPIT_TEMPLATE_REF",
            ],
            "scenarioCoverage": [
                {
                    "scenario": "Fresh adoption Contract has sufficient intent and evidence for enforced Preflight.",
                    "required": True,
                    "status": "verified",
                    "evidence": ["installer action log", ".ai/cockpit/adoption.md"],
                },
                {
                    "scenario": "Project quality remains explicitly unconfigured after adoption.",
                    "required": True,
                    "status": "verified",
                    "evidence": ["adoption Contract outOfScope", "adoption guideline"],
                },
            ],
            "verification": [
                {"check": item["check"], "result": "not_run"} for item in verification
            ],
            "guidelinesCompliance": [
                {
                    "guideline": adoption_guidelines[0],
                    "compliant": True,
                    "evidence": "Adoption verification excludes unconfigured project quality commands.",
                }
            ],
            "unknownsRemaining": [],
            "risk": {
                "level": "low",
                "detail": "Trusted approval must still be enforced by the code-hosting platform; project quality remains a documented follow-up.",
            },
            "generatedFiles": [".ai/cockpit/current_status.md"],
            "destructiveChanges": [],
            "observedIssues": [],
            "residualRisks": [
                {
                    "level": "medium",
                    "area": "project_quality",
                    "detail": "Configure and require project quality checks after adoption.",
                    "reviewRecommended": True,
                    "followUpCandidate": True,
                }
            ],
            "reviewReadiness": {
                "status": "ready_with_risks",
                "reason": "Governance bootstrap is recorded; project checks remain a follow-up.",
                "expectedReviewFocus": [
                    "Complete installation path ownership",
                    "External trusted approval",
                ],
            },
            "boundaryChecks": {
                key: "verified"
                for key in (
                    "runtimeEntrypoints",
                    "userVisibleOutput",
                    "persistence",
                    "localization",
                    "generatedArtifacts",
                    "makeEntrypoints",
                )
            },
            "userCorrectionsCaptured": [],
            "userCorrectionSolidification": [],
            "checkpointEvidence": [],
            "knownGaps": ["Project-specific quality commands are not configured by adoption."],
            "overclaimPrevention": "This record covers governance adoption only, not product quality validation.",
        }
        for path, data, detail in (
            (contract_path, contract, "create adoption Contract"),
            (summary_path, summary, "create adoption Summary"),
            (receipt_path, receipt, "create adoption Start Receipt"),
        ):
            self.record("write", path, detail)
            if not self.dry_run:
                self.write_json(path, data)
                self.created_paths.add(path)

    def finalize_adoption_records(self) -> None:
        contract_path, summary_path = self.adoption_paths()
        status_path = self.target / ".ai" / "cockpit" / "current_status.md"
        runtime_path = self.target / ".ai" / "cockpit" / "adoption-runtime-verification.json"
        self.record("write", status_path, "generate adoption Work Item status")
        self.record("write", runtime_path, "write adopter Runtime Verification evidence")
        if self.dry_run:
            return
        if not status_path.exists():
            self.created_paths.add(status_path)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        changed: dict[str, str] = {}
        for action in self.actions:
            if action.kind not in {"write", "overwrite", "append", "replace"}:
                continue
            if action.path.is_relative_to(self.target):
                changed[action.path.relative_to(self.target).as_posix()] = action.detail
        summary["changedFiles"] = [
            {"path": path, "reason": reason} for path, reason in sorted(changed.items())
        ]
        self.write_json(summary_path, summary)
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ai_generate_status.py",
                contract_path.relative_to(self.target).as_posix(),
                "--summary",
                summary_path.relative_to(self.target).as_posix(),
            ],
            cwd=self.target,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if result.returncode != 0:
            raise ValueError(f"failed to generate adoption status: {result.stderr.strip()}")
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        receipt_path = self.target / contract["startReceipt"]["path"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        checks = [
            {
                "check": item["check"],
                "result": "not_run",
                "reason": "Adopter project quality is owned by configure_ai_cockpit.",
            }
            for item in contract.get("verification", [])
            if isinstance(item, dict) and isinstance(item.get("check"), str)
        ]
        runtime = build_runtime_verification(
            contract,
            summary,
            receipt,
            source_release_tag=str(contract.get("sourceReleaseTag", "unknown")),
            source_repository=str(contract.get("sourceRepository", "unknown")),
            checks=checks,
        )
        self.write_json(runtime_path, runtime)

    def upgrade_preflight(self) -> bool:
        active_dir = self.target / ".ai" / "work-items" / "active"
        active_records = sorted(active_dir.glob("*.json")) if active_dir.exists() else []
        if active_records and not self.upgrade_with_active:
            joined = ", ".join(path.name for path in active_records)
            print(
                "ERROR: refusing to upgrade while active Work Item records exist: "
                f"{joined}. Finish/archive them first or pass --upgrade-with-active.",
                file=sys.stderr,
            )
            return False

        try:
            source_version = self.load_version(self.source / ".ai" / "cockpit" / "version.json")
            target_path = self.target / ".ai" / "cockpit" / "version.json"
            target_version = self.load_version(target_path) if target_path.exists() else None
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR: invalid upgrade version metadata: {exc}", file=sys.stderr)
            return False

        if target_version is not None:
            for key in ("distributionVersion", "contractSchema"):
                source_value = source_version[key]
                target_value = target_version[key]
                if not isinstance(source_value, int) or not isinstance(target_value, int):
                    raise ValueError(f"version metadata {key} must remain an integer")
                if source_value < target_value:
                    print(
                        f"ERROR: refusing {key} downgrade from {target_value} to {source_value}",
                        file=sys.stderr,
                    )
                    return False
            source_release = source_version.get("releaseVersion")
            target_release = target_version.get("releaseVersion")
            if isinstance(source_release, str) and isinstance(target_release, str):
                if self.release_semver(source_release) < self.release_semver(target_release):
                    print(
                        f"ERROR: refusing releaseVersion downgrade from {target_release} "
                        f"to {source_release}",
                        file=sys.stderr,
                    )
                    return False
        return True

    def prepare_upgrade_branch(self) -> bool:
        """Create an isolated upgrade branch from the adopter default branch when available."""
        remote, branch = self.base_remote, self.base_branch
        discovered_remote, discovered_branch = self.adopter_git_context()
        remote = remote or discovered_remote
        branch = branch or discovered_branch
        if remote and not branch:
            print(
                "ERROR: remote exists but default branch is unknown; pass --base-remote and --base-branch.",
                file=sys.stderr,
            )
            return False
        if not remote or not branch:
            remotes = run_git(self.target, ["remote"])
            if remotes.returncode == 0 and remotes.stdout.strip():
                print(
                    "ERROR: remote exists but default branch is unknown; pass --base-remote and --base-branch.",
                    file=sys.stderr,
                )
                return False
            print(
                "WARN: upgrade branch could not be created without a remote; continuing local-only.",
                file=sys.stderr,
            )
            return True
        branch_name = os.environ.get("AI_COCKPIT_UPGRADE_BRANCH", "upgrade/ai-cockpit")
        if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch_name) or branch_name.startswith("/"):
            print("ERROR: AI_COCKPIT_UPGRADE_BRANCH is not a valid branch name.", file=sys.stderr)
            return False
        if self.dry_run:
            print(f"DRY-RUN: would create upgrade branch {branch_name} from {remote}/{branch}")
            return True
        self.original_git_head = self.capture_git_head()
        if self.original_git_head is None:
            print("ERROR: failed to capture original Git HEAD before upgrade.", file=sys.stderr)
            return False
        for args in (
            ("fetch", remote, branch),
            ("show-ref", "--verify", f"refs/remotes/{remote}/{branch}"),
        ):
            result = run_git(self.target, list(args))
            if result.returncode != 0:
                print(
                    f"ERROR: failed to prepare upgrade branch: {result.stderr.strip()}",
                    file=sys.stderr,
                )
                return False
        if (
            run_git(self.target, ["show-ref", "--verify", f"refs/heads/{branch_name}"]).returncode
            == 0
        ):
            print(f"ERROR: upgrade branch already exists: {branch_name}", file=sys.stderr)
            return False
        created = run_git(self.target, ["switch", "--create", branch_name, f"{remote}/{branch}"])
        if created.returncode != 0:
            print(
                f"ERROR: failed to create upgrade branch: {created.stderr.strip()}", file=sys.stderr
            )
            return False
        self.created_adoption_branch = branch_name
        print(f"Created upgrade branch {branch_name} from {remote}/{branch}")
        return True

    def upgrade_paths(self) -> tuple[Path, Path]:
        active = self.target / ".ai" / "work-items" / "active"
        return (
            active / "upgrade_ai_cockpit.contract.json",
            active / "upgrade_ai_cockpit.summary.json",
        )

    def create_upgrade_records(self) -> None:
        contract_path, summary_path = self.upgrade_paths()
        base_commit = (
            run_git(self.target, ["rev-parse", "--verify", "HEAD"]).stdout.strip()
            or "unknown-local-base"
        )
        source_release, source_repository = self.source_context()
        verification = [
            {"check": check, "required": True}
            for check in (
                "aiWorkItem",
                "aiScope",
                "aiAgentRisk",
                "aiSummary",
                "aiStatus",
                "aiStatusCheck",
            )
        ]
        contract = {
            "contractVersion": 2,
            "workItemId": "upgrade_ai_cockpit",
            "mode": "code",
            "title": "Upgrade AI Cockpit governance",
            "baseCommit": base_commit,
            "baseRemote": self.adopter_git_context()[0] or "local source",
            "baseBranch": self.adopter_git_context()[1] or "local branch",
            "sourceReleaseTag": source_release,
            "sourceRepository": source_repository,
            "baselineDirtyPaths": [],
            "scope": [
                ".ai/**",
                ".cursor/**",
                "scripts/**",
                "Makefile.ai",
                "Makefile.ai.stack",
                "AGENTS.md",
                "GEMINI.md",
                "CLAUDE.md",
                ".gitignore",
                "Makefile",
            ],
            "outOfScope": [
                "Product source changes",
                "Automatic commit, push, PR, merge, or branch deletion",
            ],
            "sources": [
                {
                    "path": ".ai/cockpit/version.json",
                    "reason": "Upgrade before/after version identity.",
                },
                {
                    "path": "installer action log",
                    "reason": "Managed file diff and rollback evidence.",
                },
            ],
            "unknowns": [],
            "notCodable": False,
            "riskAssessment": {
                "level": "high",
                "riskTypes": ["upgrade_integrity"],
                "reason": "Upgrade replaces managed governance files and must remain reviewable and reversible.",
            },
            "agentCapability": {
                "canImplement": True,
                "canVerify": True,
                "needsHumanDecision": False,
                "blockedReason": "",
            },
            "executionDecision": {
                "status": "continue",
                "reason": "User invoked the upgrade workflow.",
            },
            "preReviewWarnings": [
                "Review managed-file diff, source/target versions, and rollback backup before commit."
            ],
            "checkpointPolicy": {
                "requiredBeforeFinish": False,
                "requiredStages": [],
                "reason": "Installer-generated bounded upgrade record.",
            },
            "acceptance": [
                "Upgrade creates an active Contract and Summary on a dedicated upgrade branch when a remote default branch is discoverable.",
                "Contract/Summary record source and target versions, managed file changes, and rollback backup paths.",
                "Upgrade remains review-only: installer performs no commit, push, PR, merge, or branch deletion.",
            ],
            "guidelines": [
                "Upgrade must fail closed when active Work Items exist unless --upgrade-with-active is explicit.",
                "Rollback backups must remain available until the upgrade is reviewed.",
            ],
            "verification": verification,
            "destructiveChangePolicy": {
                "allowed": False,
                "requiresHumanApproval": True,
                "allowPatterns": [],
            },
            "restrictedWriteApproval": {
                "approved": True,
                "approvedBy": "user",
                "reason": "User authorized the complete implementation loop.",
            },
            "rollbackNote": "Restore the recorded upgrade-backups directory and revert the Work Item branch.",
        }
        receipt = build_receipt(contract, project_root=self.target)
        contract["startReceipt"] = receipt_binding(receipt)
        summary = {
            "summaryVersion": 2,
            "workItemId": "upgrade_ai_cockpit",
            "contractPath": contract_path.relative_to(self.target).as_posix(),
            "changedFiles": [],
            "sourcesUsed": [".ai/cockpit/version.json", "installer action log"],
            "verification": [
                {"check": item["check"], "result": "not_run"} for item in verification
            ],
            "guidelinesCompliance": [
                {
                    "guideline": item,
                    "compliant": True,
                    "evidence": "Installer enforces this boundary.",
                }
                for item in cast(list[str], contract["guidelines"])
            ],
            "unknownsRemaining": [],
            "risk": {
                "level": "high",
                "detail": "Review the managed diff and rollback backup before commit.",
            },
            "generatedFiles": [".ai/cockpit/current_status.md"],
            "destructiveChanges": [],
            "observedIssues": [],
            "residualRisks": [
                {
                    "level": "medium",
                    "area": "rollback",
                    "detail": "Backup cleanup remains a human-reviewed follow-up.",
                    "reviewRecommended": True,
                    "followUpCandidate": True,
                }
            ],
            "reviewReadiness": {
                "status": "ready_with_risks",
                "reason": "Upgrade evidence is recorded for review.",
                "expectedReviewFocus": [
                    "Source/target version identity",
                    "Managed file diff",
                    "Rollback backup",
                ],
            },
            "boundaryChecks": {
                key: "verified"
                for key in (
                    "runtimeEntrypoints",
                    "userVisibleOutput",
                    "persistence",
                    "localization",
                    "generatedArtifacts",
                    "makeEntrypoints",
                )
            },
            "userCorrectionsCaptured": [],
            "userCorrectionSolidification": [],
            "checkpointEvidence": [],
            "knownGaps": [],
            "overclaimPrevention": "Do not report upgrade completion as merged or published.",
        }
        for path, data, detail in (
            (contract_path, contract, "create upgrade Contract"),
            (summary_path, summary, "create upgrade Summary"),
            (self.target / receipt["receiptPath"], receipt, "create upgrade Start Receipt"),
        ):
            self.record("write", path, detail)
            if not self.dry_run:
                self.write_json(path, data)
                self.created_paths.add(path)

    def finalize_upgrade_records(self) -> None:
        contract_path, summary_path = self.upgrade_paths()
        if self.dry_run or not summary_path.exists():
            return
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        changed = {
            action.path.relative_to(self.target).as_posix(): action.detail
            for action in self.actions
            if action.kind in {"write", "overwrite", "append", "replace"}
            and action.path.is_relative_to(self.target)
        }
        summary["changedFiles"] = [
            {"path": path, "reason": reason} for path, reason in sorted(changed.items())
        ]
        summary["rollbackEvidence"] = {
            "backupRoot": self.backup_dir.relative_to(self.target).as_posix(),
            "sourceVersion": self.load_version(self.source / ".ai" / "cockpit" / "version.json"),
            "targetVersion": self.load_version(self.target / ".ai" / "cockpit" / "version.json"),
        }
        summary["ownershipDecisions"] = self.upgrade_conflicts
        self.write_json(summary_path, summary)

    @staticmethod
    def release_semver(value: str) -> tuple[int, int, int]:
        return installer_release_semver(value)

    @staticmethod
    def load_version(path: Path) -> dict[str, int | str]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path}: root must be a JSON object")
        result: dict[str, int | str] = {}
        for key in ("distributionVersion", "contractSchema"):
            value = data.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{path}: {key} must be a positive integer")
            result[key] = value
        release_version = data.get("releaseVersion")
        if release_version is not None:
            if not isinstance(release_version, str):
                raise ValueError(f"{path}: releaseVersion must be a string")
            Installer.release_semver(release_version)
            result["releaseVersion"] = release_version
        return result

    def record(self, kind: str, path: Path, detail: str) -> None:
        self.actions.append(Action(kind, path, detail))
        print(
            f"{kind}: {path.relative_to(self.target) if path.is_relative_to(self.target) else path} - {detail}"
        )

    def copy_tree(self, relative: str) -> None:
        for src, dst in self.tree_copy_pairs(relative):
            self.copy_path(src, dst)

    def install_initial_status(self) -> None:
        active_dir = self.target / ".ai" / "work-items" / "active"
        if active_dir.exists() and any(active_dir.glob("*.json")):
            self.record(
                "skip",
                self.target / ".ai" / "cockpit" / "current_status.md",
                "preserve active Work Item status",
            )
            return
        dst = self.target / ".ai" / "cockpit" / "current_status.md"
        self.assert_safe_destination(dst)
        existed = dst.exists()
        if existed:
            self.backup_path(dst)
        self.record(
            "write" if not existed else "overwrite", dst, "generate no-active Work Item status"
        )
        if self.dry_run:
            return
        if self.has_initial_commit():
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/ai_generate_status.py",
                    "--no-active",
                    "--output",
                    dst.relative_to(self.target).as_posix(),
                ],
                cwd=self.target,
                text=True,
                capture_output=True,
                check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            if result.returncode != 0:
                raise ValueError(
                    f"failed to generate no-active Work Item status: {result.stderr.strip()}"
                )
        else:
            write_no_active_status(dst)
        if not existed:
            self.created_paths.add(dst)

    def install_lifecycle_facts(self) -> None:
        if self.dry_run:
            return
        fact_paths = [self.target / ".ai" / "install" / name for name in FACT_NAMES]
        for path in fact_paths:
            self.record("write", path, "write installed lifecycle fact")
        write_fact_bundle(
            source=self.source,
            target=self.target,
            distribution_version=self.load_version(
                self.source / ".ai" / "cockpit" / "version.json"
            ),
        )
        self.created_paths.update(self.target / ".ai" / "install" / name for name in FACT_NAMES)

    def copy_scripts(self) -> None:
        self.copy_path(
            self.source / "scripts" / CATALOG_NAME,
            self.target / "scripts" / CATALOG_NAME,
        )
        for name in sorted(SCRIPT_NAMES):
            self.copy_path(
                self.source / "scripts" / name, self.target / "scripts" / name, executable=True
            )

    def install_glossary(self) -> None:
        src = self.source / "templates" / "glossary.md"
        dst = self.target / ".ai" / "glossary.md"
        if dst.exists() and not self.replace_glossary:
            self.record("skip", dst, "preserve project-owned glossary")
            return
        existed = dst.exists()
        if existed:
            self.backup_path(dst)
        self.record("overwrite" if existed else "write", dst, "install project glossary template")
        if self.dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if not existed:
            self.created_paths.add(dst)

    def copy_file(self, src_relative: str, dst_relative: str) -> None:
        self.copy_path(self.source / src_relative, self.target / dst_relative)

    def copy_path(self, src: Path, dst: Path, *, executable: bool = False) -> None:
        self.assert_safe_destination(dst)
        existed = dst.exists()
        relative = dst.relative_to(self.target).as_posix()
        project_owned_boundary = is_project_owned(relative)
        if self.upgrade and existed and src.read_bytes() != dst.read_bytes():
            if project_owned_boundary or not self.confirm_upgrade_conflicts:
                decision = {
                    "path": relative,
                    "classification": "Project-owned" if project_owned_boundary else "Diverged",
                    "decision": "preserved",
                    "reason": "Target differs from template baseline; review manually before adopting template changes.",
                    "summary": "Target content differs from the template-managed content.",
                    "recommendation": "Confirm the project-owned decision or keep the target file unchanged.",
                }
                self.upgrade_conflicts.append(decision)
                self.upgrade_conflict_report = build_report(
                    self.upgrade_conflicts,
                    source_version=self.load_version(
                        self.source / ".ai" / "cockpit" / "version.json"
                    ),
                    target_version=self.load_version(
                        self.target / ".ai" / "cockpit" / "version.json"
                    ),
                )
                report_path = self.target / ".ai" / "cockpit" / "upgrade-conflict-report.json"
                if not self.dry_run:
                    report_path.parent.mkdir(parents=True, exist_ok=True)
                    report_path.write_text(
                        json.dumps(self.upgrade_conflict_report, indent=2) + "\n", encoding="utf-8"
                    )
                if upgrade_conflict_gate(
                    self.upgrade_conflict_report, confirmed=self.confirm_upgrade_conflicts
                ):
                    raise ValueError(
                        "upgrade conflict report requires human confirmation; "
                        "review .ai/cockpit/upgrade-conflict-report.json and pass "
                        "--confirm-upgrade-conflicts"
                    )
                if project_owned_boundary:
                    self.record("skip", dst, "preserve project-owned or diverged governance file")
                    return
        if existed and not (self.force or self.upgrade):
            self.record("skip", dst, "already exists")
            return
        if existed:
            self.backup_path(dst)
        self.record(
            "write" if not existed else "overwrite", dst, f"from {src.relative_to(self.source)}"
        )
        if self.dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if not existed:
            self.created_paths.add(dst)
        if executable:
            dst.chmod(dst.stat().st_mode | 0o111)

    def backup_path(self, path: Path) -> None:
        self.assert_safe_destination(path)
        if path in self.backups:
            return
        relative = path.relative_to(self.target)
        backup = self.backup_dir / relative
        self.record("backup", backup, f"before upgrading {relative}")
        if self.dry_run:
            return
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        self.backups.setdefault(path, backup)

    def assert_safe_destination(self, path: Path) -> None:
        """Reject symlinked destination components so installation stays in target."""
        try:
            relative = path.relative_to(self.target)
        except ValueError as exc:
            raise RuntimeError(f"refusing destination outside target: {path}") from exc
        current = self.target
        for component in relative.parts:
            current /= component
            if current.is_symlink():
                raise RuntimeError(
                    f"refusing symlinked destination: {current.relative_to(self.target)}"
                )

    def install_agent_doc(self, name: str) -> None:
        dst = self.target / name
        self.assert_safe_destination(dst)
        if not dst.exists():
            self.record("write", dst, "install managed AI Cockpit section")
            if not self.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(self.agent_section(), encoding="utf-8")
                self.created_paths.add(dst)
            return
        text = dst.read_text(encoding="utf-8")
        if AGENT_MARKER in text:
            if not (self.force or self.upgrade):
                self.record("skip", dst, "AI Cockpit section already present")
                return
            self.backup_path(dst)
            section = self.agent_section()
            start = text.index(AGENT_MARKER)
            end_index = text.find(AGENT_END_MARKER, start)
            suffix = text[end_index + len(AGENT_END_MARKER) :]
            replacement = text[:start].rstrip() + "\n\n" + section + suffix
            self.record("replace", dst, "replace managed AI Cockpit section")
            if not self.dry_run:
                dst.write_text(replacement, encoding="utf-8")
            return
        section = self.agent_section()
        detail = "add AI Cockpit section"
        if self.upgrade:
            detail = "preserve unmarked agent rules and add managed section"
        self.backup_path(dst)
        self.record("append", dst, detail)
        if self.dry_run:
            return
        with dst.open("a", encoding="utf-8") as handle:
            if text and not text.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + section)

    def agent_section(self) -> str:
        title = "AI Cockpit Rules"
        body = (
            (self.source / "templates" / "agents" / "AI_COCKPIT_RULES.md")
            .read_text(encoding="utf-8")
            .strip()
        )
        return f"{AGENT_MARKER}\n\n## {title}\n\n{body}\n\n{AGENT_END_MARKER}\n"

    def append_makefile_include(self) -> None:
        dst = self.target / "Makefile"
        self.assert_safe_destination(dst)
        include_line = "include Makefile.ai"
        if not dst.exists():
            self.record("write", dst, "create Makefile with AI Cockpit include")
            if not self.dry_run:
                dst.write_text(f"{include_line}\n", encoding="utf-8")
                self.created_paths.add(dst)
            return
        text = dst.read_text(encoding="utf-8")
        active_include = re.compile(r"^\s*include\s+Makefile\.ai\s*(?:#.*)?$")
        if any(active_include.match(line) for line in text.splitlines()):
            self.record("skip", dst, "Makefile.ai already included")
            return
        self.backup_path(dst)
        self.record("append", dst, "include Makefile.ai")
        if self.dry_run:
            return
        with dst.open("a", encoding="utf-8") as handle:
            if text and not text.endswith("\n"):
                handle.write("\n")
            handle.write(f"\n{include_line}\n")

    def install_gitignore(self) -> None:
        dst = self.target / ".gitignore"
        self.assert_safe_destination(dst)
        existed = dst.exists()
        text = dst.read_text(encoding="utf-8") if dst.exists() else ""
        missing_rules = [rule for rule in GITIGNORE_RULES if rule not in text.splitlines()]
        if GITIGNORE_MARKER in text and not missing_rules:
            self.record("skip", dst, "AI Cockpit local-state rules already present")
            return
        if dst.exists():
            self.backup_path(dst)
        self.record(
            "append" if dst.exists() else "write",
            dst,
            "add missing AI Cockpit local-state ignore rules",
        )
        if self.dry_run:
            return
        prefix = text
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        if prefix:
            prefix += "\n"
        if GITIGNORE_MARKER in text:
            addition = "\n".join(missing_rules) + "\n"
        else:
            addition = GITIGNORE_SECTION
        dst.write_text(prefix + addition, encoding="utf-8")
        if not existed:
            self.created_paths.add(dst)

    def print_summary(self) -> None:
        writes, skips = action_counts(self.actions)
        print("")
        print(
            f"AI Cockpit install {'dry run ' if self.dry_run else ''}complete: {writes} write/append action(s), {skips} skipped."
        )
        if self.backups:
            print(f"Backups: {self.backup_dir.relative_to(self.target)}")
        print("")
        print("Next steps:")
        if self.create_adoption:
            print("  1. Run: make ai-finish TASK=adopt_ai_cockpit")
            print(
                "  2. HUMAN APPROVAL REQUIRED before commit and push; human review/merge PR; approve ai-close-work-item after merge."
            )
            print("  3. In PR CI run: make check-ai-pr AI_BASE_COMMIT=<pre-adoption-commit>")
            print("  4. Run: make ai-onboard; validate Guards; run make check-ai-adoption-ready")
            return
        if not self.has_initial_commit():
            print("  WARNING: ai-start requires a Git repository with at least one commit.")
        if not self.update_makefile:
            print("  1. Add this line to your Makefile: include Makefile.ai")
            print('  2. Run: make ai-start TASK=example_change TITLE="Example change" MODE=code')
            print("  3. Edit the generated Contract before changing project files.")
            print("  4. Finish with: make ai-finish TASK=example_change")
            print("  5. In PR CI run: make check-ai-pr AI_BASE_COMMIT=<merge-base-sha>")
        else:
            print('  1. Run: make ai-start TASK=example_change TITLE="Example change" MODE=code')
            print("  2. Edit the generated Contract before changing project files.")
            print("  3. Finish with: make ai-finish TASK=example_change")
            print("  4. In PR CI run: make check-ai-pr AI_BASE_COMMIT=<merge-base-sha>")

    def has_initial_commit(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=self.target,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except OSError:
            return False
        return result.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install AI Cockpit into an existing repository.")
    parser.add_argument(
        "--source",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to the ai-cockpit-template source.",
    )
    parser.add_argument("--target", default=".", help="Target repository root.")
    parser.add_argument(
        "--stack", default="generic", choices=sorted(STACKS), help="Project stack preset."
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing AI Cockpit files.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show actions without writing files."
    )
    parser.add_argument(
        "--with-examples", action="store_true", help="Copy examples/ into the target repository."
    )
    parser.add_argument(
        "--update-makefile",
        action="store_true",
        help="Append include Makefile.ai to the target Makefile.",
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Back up and replace managed AI Cockpit files and agent marker sections.",
    )
    parser.add_argument(
        "--create-adoption",
        action="store_true",
        help="Create an auditable first-adoption Work Item; requires a clean repository with an initial commit.",
    )
    parser.add_argument(
        "--replace-glossary",
        action="store_true",
        help="Back up and explicitly replace the project-owned .ai/glossary.md template.",
    )
    parser.add_argument(
        "--upgrade-with-active",
        action="store_true",
        help="Allow a high-risk upgrade while active Work Item records exist.",
    )
    parser.add_argument(
        "--base-remote", help="Explicit adopter remote for upgrade/adoption lifecycle."
    )
    parser.add_argument(
        "--base-branch", help="Explicit adopter base branch for upgrade/adoption lifecycle."
    )
    parser.add_argument(
        "--confirm-upgrade-conflicts",
        action="store_true",
        help="Explicitly continue after reviewing the generated upgrade conflict report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return Installer(
        source=Path(args.source),
        target=Path(args.target),
        stack=args.stack,
        force=args.force,
        dry_run=args.dry_run,
        with_examples=args.with_examples,
        update_makefile=args.update_makefile,
        upgrade=args.upgrade,
        upgrade_with_active=args.upgrade_with_active,
        replace_glossary=args.replace_glossary,
        create_adoption=args.create_adoption,
        base_remote=args.base_remote,
        base_branch=args.base_branch,
        confirm_upgrade_conflicts=args.confirm_upgrade_conflicts,
    ).install()


if __name__ == "__main__":
    sys.exit(main())
