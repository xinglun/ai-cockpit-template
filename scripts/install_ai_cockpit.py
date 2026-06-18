#!/usr/bin/env python3
"""Install AI Cockpit into an existing repository."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_generate_status import write_no_active_status


STACKS = {
    "generic",
    "rust",
    "flutter",
    "typescript",
    "python",
    "go",
    "java",
    "android",
    "kotlin",
    "swift",
    "ruby",
    "php",
    "csharp",
}
SCRIPT_NAMES = {
    "ai_archive_work_item.py",
    "ai_checkpoint.py",
    "ai_check_agent_risk.py",
    "ai_check_backtrack.py",
    "ai_check_coverage_guard.py",
    "ai_check_guidelines.py",
    "ai_check_guards.py",
    "ai_check_pr.py",
    "ai_check_review_policy.py",
    "ai_check_scope.py",
    "ai_check_status.py",
    "ai_check_status_consistency.py",
    "ai_check_summary.py",
    "ai_check_work_item.py",
    "ai_common.py",
    "ai_finish.py",
    "ai_generate_status.py",
    "ai_observability.py",
    "ai_start.py",
}
AGENT_MARKER = "<!-- AI_COCKPIT_SECTION -->"
AGENT_END_MARKER = "<!-- /AI_COCKPIT_SECTION -->"
GITIGNORE_MARKER = "# AI Cockpit local state"
GITIGNORE_SECTION = """# AI Cockpit local state
.ai/work-items/active/*.contract.json
.ai/work-items/active/*.summary.json
.ai/work-items/active/*.review.json
.ai/cockpit/upgrade-backups/
target/ai_*.json
target/ai_*.jsonl
"""
GITIGNORE_RULES = tuple(
    line for line in GITIGNORE_SECTION.splitlines() if line and not line.startswith("#")
)


@dataclass(frozen=True)
class Action:
    kind: str
    path: Path
    detail: str


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
        self.backup_dir = self.target / ".ai" / "cockpit" / "upgrade-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.actions: list[Action] = []
        self.backups: dict[Path, Path] = {}
        self.created_paths: set[Path] = set()

    def install(self) -> int:
        if not self.source.exists():
            print(f"ERROR: source template does not exist: {self.source}", file=sys.stderr)
            return 2
        if self.stack not in STACKS:
            print(f"ERROR: unsupported stack {self.stack}; expected one of {sorted(STACKS)}", file=sys.stderr)
            return 2
        if self.upgrade and not self.upgrade_preflight():
            return 2
        self.target.mkdir(parents=True, exist_ok=True)
        try:
            self.copy_tree(".ai")
            self.install_initial_status()
            self.copy_tree(".cursor")
            self.copy_scripts()
            self.copy_file("templates/make/Makefile.ai", "Makefile.ai")
            self.copy_file(f"templates/stacks/{self.stack}.mk", "Makefile.ai.stack")
            self.copy_file("templates/glossary.md", ".ai/glossary.md")
            if self.with_examples:
                self.copy_tree("examples")
            self.install_agent_doc("AGENTS.md")
            self.install_agent_doc("GEMINI.md")
            self.install_agent_doc("CLAUDE.md")
            self.install_gitignore()
            if self.update_makefile:
                self.append_makefile_include()
            if self.upgrade:
                self.validate_upgraded_installation()
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            if self.upgrade and not self.dry_run:
                self.rollback_upgrade()
            print(f"ERROR: installation failed: {exc}", file=sys.stderr)
            return 2

        self.print_summary()
        return 0

    def validate_upgraded_installation(self) -> None:
        if self.dry_run:
            return
        source_version = self.load_version(self.source / ".ai" / "cockpit" / "version.json")
        installed_version = self.load_version(self.target / ".ai" / "cockpit" / "version.json")
        if installed_version != source_version:
            raise ValueError("installed version metadata does not match the source distribution")
        required = [
            self.target / "Makefile.ai",
            *(self.target / "scripts" / name for name in SCRIPT_NAMES),
        ]
        missing = [path.relative_to(self.target).as_posix() for path in required if not path.is_file()]
        if missing:
            raise ValueError(f"upgraded installation is missing managed files: {', '.join(missing)}")

    def rollback_upgrade(self) -> None:
        for original, backup in reversed(list(self.backups.items())):
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, original)
        for path in sorted(self.created_paths, key=lambda item: len(item.parts), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
        print(f"Upgrade rolled back from backups in {self.backup_dir.relative_to(self.target)}")

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
                if source_version[key] < target_version[key]:
                    print(
                        f"ERROR: refusing {key} downgrade from {target_version[key]} "
                        f"to {source_version[key]}",
                        file=sys.stderr,
                    )
                    return False
        return True

    @staticmethod
    def load_version(path: Path) -> dict[str, int]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path}: root must be a JSON object")
        result: dict[str, int] = {}
        for key in ("distributionVersion", "contractSchema"):
            value = data.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{path}: {key} must be a positive integer")
            result[key] = value
        return result

    def record(self, kind: str, path: Path, detail: str) -> None:
        self.actions.append(Action(kind, path, detail))
        print(f"{kind}: {path.relative_to(self.target) if path.is_relative_to(self.target) else path} - {detail}")

    def copy_tree(self, relative: str) -> None:
        src = self.source / relative
        dst = self.target / relative
        if not src.exists():
            return
        for item in src.rglob("*"):
            if item.is_dir():
                continue
            rel = item.relative_to(src)
            if relative == ".ai" and rel.as_posix() == "cockpit/current_status.md":
                continue
            if relative == ".ai" and len(rel.parts) >= 3 and rel.parts[:2] == ("work-items", "active") and rel.name != ".gitkeep":
                continue
            if relative == ".ai" and len(rel.parts) >= 3 and rel.parts[:2] == ("work-items", "archive") and rel.name != ".gitkeep":
                continue
            self.copy_path(item, dst / rel)

    def install_initial_status(self) -> None:
        active_dir = self.target / ".ai" / "work-items" / "active"
        if active_dir.exists() and any(active_dir.glob("*.json")):
            self.record("skip", self.target / ".ai" / "cockpit" / "current_status.md", "preserve active Work Item status")
            return
        dst = self.target / ".ai" / "cockpit" / "current_status.md"
        existed = dst.exists()
        if existed and self.upgrade:
            self.backup_path(dst)
        self.record("write" if not existed else "overwrite", dst, "generate no-active Work Item status")
        if self.dry_run:
            return
        write_no_active_status(dst)
        if self.upgrade and not existed:
            self.created_paths.add(dst)

    def copy_scripts(self) -> None:
        for name in sorted(SCRIPT_NAMES):
            self.copy_path(self.source / "scripts" / name, self.target / "scripts" / name, executable=True)

    def copy_file(self, src_relative: str, dst_relative: str) -> None:
        self.copy_path(self.source / src_relative, self.target / dst_relative)

    def copy_path(self, src: Path, dst: Path, *, executable: bool = False) -> None:
        existed = dst.exists()
        if existed and not (self.force or self.upgrade):
            self.record("skip", dst, "already exists")
            return
        if existed and self.upgrade:
            self.backup_path(dst)
        self.record("write" if not existed else "overwrite", dst, f"from {src.relative_to(self.source)}")
        if self.dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if self.upgrade and not existed:
            self.created_paths.add(dst)
        if executable:
            dst.chmod(dst.stat().st_mode | 0o111)

    def backup_path(self, path: Path) -> None:
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

    def install_agent_doc(self, name: str) -> None:
        src = self.source / name
        dst = self.target / name
        if not dst.exists():
            self.record("write", dst, "install managed AI Cockpit section")
            if not self.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(self.agent_section(src), encoding="utf-8")
                if self.upgrade:
                    self.created_paths.add(dst)
            return
        text = dst.read_text(encoding="utf-8")
        if AGENT_MARKER in text:
            if not (self.force or self.upgrade):
                self.record("skip", dst, "AI Cockpit section already present")
                return
            if self.upgrade:
                self.backup_path(dst)
            section = self.agent_section(src)
            start = text.index(AGENT_MARKER)
            end_index = text.find(AGENT_END_MARKER, start)
            suffix = "" if end_index < 0 else text[end_index + len(AGENT_END_MARKER):]
            replacement = text[:start].rstrip() + "\n\n" + section + suffix
            self.record("replace", dst, "replace managed AI Cockpit section")
            if not self.dry_run:
                dst.write_text(replacement, encoding="utf-8")
            return
        section = self.agent_section(src)
        if self.upgrade:
            self.backup_path(dst)
            self.record("replace", dst, "replace legacy unmarked agent rules with managed section")
            if not self.dry_run:
                dst.write_text(section, encoding="utf-8")
            return
        self.record("append", dst, "add AI Cockpit section")
        if self.dry_run:
            return
        with dst.open("a", encoding="utf-8") as handle:
            if text and not text.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + section)

    def agent_section(self, src: Path) -> str:
        title = "AI Cockpit Rules"
        body = src.read_text(encoding="utf-8").strip()
        return f"{AGENT_MARKER}\n\n## {title}\n\n{body}\n\n{AGENT_END_MARKER}\n"

    def append_makefile_include(self) -> None:
        dst = self.target / "Makefile"
        include_line = "include Makefile.ai"
        if not dst.exists():
            self.record("write", dst, "create Makefile with AI Cockpit include")
            if not self.dry_run:
                dst.write_text(f"{include_line}\n", encoding="utf-8")
                if self.upgrade:
                    self.created_paths.add(dst)
            return
        text = dst.read_text(encoding="utf-8")
        if include_line in text:
            self.record("skip", dst, "Makefile.ai already included")
            return
        if self.upgrade:
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
        text = dst.read_text(encoding="utf-8") if dst.exists() else ""
        missing_rules = [rule for rule in GITIGNORE_RULES if rule not in text.splitlines()]
        if GITIGNORE_MARKER in text and not missing_rules:
            self.record("skip", dst, "AI Cockpit local-state rules already present")
            return
        if dst.exists() and self.upgrade:
            self.backup_path(dst)
        self.record("append" if dst.exists() else "write", dst, "add missing AI Cockpit local-state ignore rules")
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

    def print_summary(self) -> None:
        writes = sum(1 for action in self.actions if action.kind in {"write", "overwrite", "append", "replace"})
        skips = sum(1 for action in self.actions if action.kind == "skip")
        print("")
        print(f"AI Cockpit install {'dry run ' if self.dry_run else ''}complete: {writes} write/append action(s), {skips} skipped.")
        if self.upgrade:
            print(f"Upgrade backups: {self.backup_dir.relative_to(self.target)}")
        print("")
        print("Next steps:")
        if not self.update_makefile:
            print("  1. Add this line to your Makefile: include Makefile.ai")
            print("  2. Run: make ai-start TASK=example_change TITLE=\"Example change\" MODE=code")
            print("  3. Edit the generated Contract before changing project files.")
            print("  4. Finish with: make ai-finish TASK=example_change")
            print("  5. In PR CI run: make check-ai-pr AI_BASE_COMMIT=<merge-base-sha>")
        else:
            print("  1. Run: make ai-start TASK=example_change TITLE=\"Example change\" MODE=code")
            print("  2. Edit the generated Contract before changing project files.")
            print("  3. Finish with: make ai-finish TASK=example_change")
            print("  4. In PR CI run: make check-ai-pr AI_BASE_COMMIT=<merge-base-sha>")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install AI Cockpit into an existing repository.")
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1]), help="Path to the ai-cockpit-template source.")
    parser.add_argument("--target", default=".", help="Target repository root.")
    parser.add_argument("--stack", default="generic", choices=sorted(STACKS), help="Project stack preset.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing AI Cockpit files.")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing files.")
    parser.add_argument("--with-examples", action="store_true", help="Copy examples/ into the target repository.")
    parser.add_argument("--update-makefile", action="store_true", help="Append include Makefile.ai to the target Makefile.")
    parser.add_argument("--upgrade", action="store_true", help="Back up and replace managed AI Cockpit files and agent marker sections.")
    parser.add_argument(
        "--upgrade-with-active",
        action="store_true",
        help="Allow a high-risk upgrade while active Work Item records exist.",
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
    ).install()


if __name__ == "__main__":
    sys.exit(main())
