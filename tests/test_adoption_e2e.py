import json
import subprocess
import sys
from pathlib import Path

import install_ai_cockpit as installer_mod
from install_ai_cockpit import Installer, adoption_preflight_warnings


ROOT = Path(__file__).resolve().parents[1]


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def clone_adopter_with_remote(tmp_path: Path) -> Path:
    """remote default branch を持つ adopter clone を用意する。"""
    seed = tmp_path / "seed"
    remote = tmp_path / "project.git"
    target = tmp_path / "target"
    seed.mkdir()
    assert run(seed, "git", "init", "-q", "-b", "main").returncode == 0
    assert run(seed, "git", "config", "user.email", "test@example.invalid").returncode == 0
    assert run(seed, "git", "config", "user.name", "Test").returncode == 0
    (seed / "README.md").write_text("# Remote project\n", encoding="utf-8")
    assert run(seed, "git", "add", "README.md").returncode == 0
    assert run(seed, "git", "commit", "-qm", "initial").returncode == 0
    assert run(seed, "git", "clone", "--bare", ".", str(remote)).returncode == 0
    assert run(tmp_path, "git", "clone", "-q", str(remote), str(target)).returncode == 0
    assert run(target, "git", "config", "user.email", "test@example.invalid").returncode == 0
    assert run(target, "git", "config", "user.name", "Test").returncode == 0
    return target


def current_head(target: Path) -> tuple[str, str | None]:
    commit = run(target, "git", "rev-parse", "HEAD").stdout.strip()
    branch = run(target, "git", "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch.returncode == 0 and branch.stdout.strip():
        return commit, branch.stdout.strip()
    return commit, None


def adoption_branch_exists(target: Path, name: str = "adopt/ai-cockpit") -> bool:
    result = run(target, "git", "show-ref", "--verify", f"refs/heads/{name}")
    return result.returncode == 0


def test_first_adoption_finishes_and_passes_complete_pr_check(tmp_path):
    assert run(tmp_path, "git", "init", "-q").returncode == 0
    assert run(tmp_path, "git", "config", "user.email", "test@example.invalid").returncode == 0
    assert run(tmp_path, "git", "config", "user.name", "Test").returncode == 0
    (tmp_path / "README.md").write_text("# Existing project\n", encoding="utf-8")
    assert run(tmp_path, "git", "add", "README.md").returncode == 0
    assert run(tmp_path, "git", "commit", "-qm", "initial").returncode == 0
    base = run(tmp_path, "git", "rev-parse", "HEAD").stdout.strip()
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )

    assert installer.install() == 0
    contract = json.loads(
        (tmp_path / ".ai" / "work-items" / "active" / "adopt_ai_cockpit.contract.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["baseCommit"] == base
    release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    assert contract["sourceReleaseTag"] == release["releaseTag"]
    assert contract["sourceRepository"] == "local source"
    assert contract["sources"] == [
        {
            "path": ".ai/cockpit/adoption.md",
            "reason": "Installed first-adoption and production-readiness workflow.",
        }
    ]
    assert (tmp_path / ".ai" / "cockpit" / "adoption.md").is_file()
    contract = tmp_path / ".ai" / "work-items" / "active" / "adopt_ai_cockpit.contract.json"
    assert contract.is_file()
    finish = run(
        tmp_path,
        "make",
        "ai-finish",
        "TASK=adopt_ai_cockpit",
        f"PYTHON={sys.executable}",
    )
    assert finish.returncode == 0, finish.stdout + finish.stderr
    pr_check = run(
        tmp_path,
        "make",
        "check-ai-pr",
        f"AI_BASE_COMMIT={base}",
        f"PYTHON={sys.executable}",
    )
    assert pr_check.returncode == 0, pr_check.stdout + pr_check.stderr


def test_quick_install_creates_adoption_branch_from_remote_head(tmp_path):
    target = clone_adopter_with_remote(tmp_path)

    installer = Installer(
        source=ROOT,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )
    assert installer.install() == 0
    assert run(target, "git", "branch", "--show-current").stdout.strip() == "adopt/ai-cockpit"
    remote_base = run(target, "git", "rev-parse", "origin/main").stdout.strip()
    contract = json.loads(
        (target / ".ai/work-items/active/adopt_ai_cockpit.contract.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["baseRemote"] == "origin"
    assert contract["baseBranch"] == "main"
    assert contract["baseCommit"] == remote_base


def test_dry_run_create_adoption_performs_no_git_mutation(tmp_path, monkeypatch, capsys):
    target = clone_adopter_with_remote(tmp_path)
    before_commit, before_branch = current_head(target)
    git_commands: list[list[str]] = []
    real_run = installer_mod.subprocess.run

    def tracking_run(command, *args, **kwargs):
        if command and command[0] == "git":
            git_commands.append([str(part) for part in command])
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(installer_mod.subprocess, "run", tracking_run)
    installer = Installer(
        source=ROOT,
        target=target,
        stack="generic",
        force=False,
        dry_run=True,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )

    assert installer.install() == 0
    after_commit, after_branch = current_head(target)
    assert (after_commit, after_branch) == (before_commit, before_branch)
    assert not adoption_branch_exists(target)
    verbs = []
    for command in git_commands:
        parts = [part for part in command[1:] if not part.startswith("--")]
        if parts:
            verbs.append(parts[0])
    assert "fetch" not in verbs
    assert "switch" not in verbs
    assert "checkout" not in verbs
    assert not any(
        len(command) >= 2 and command[0] == "branch" and command[1] in {"-D", "-d", "-m", "-c"}
        for command in (
            [part for part in item[1:] if not part.startswith("--")] for item in git_commands
        )
    )
    assert "DRY-RUN: would create adoption branch adopt/ai-cockpit" in capsys.readouterr().out


def test_marker_failure_happens_before_branch_mutation(tmp_path, capsys):
    target = clone_adopter_with_remote(tmp_path)
    (target / "AGENTS.md").write_text(
        "<!-- AI_COCKPIT_SECTION -->\nbroken without end marker\n",
        encoding="utf-8",
    )
    assert run(target, "git", "add", "AGENTS.md").returncode == 0
    assert run(target, "git", "commit", "-qm", "broken markers").returncode == 0
    before_commit, before_branch = current_head(target)

    installer = Installer(
        source=ROOT,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )
    assert installer.install() == 2
    error = capsys.readouterr().err
    assert "malformed AI Cockpit markers" in error
    assert (current_head(target)) == (before_commit, before_branch)
    assert not adoption_branch_exists(target)
    assert not (target / ".ai").exists()


def test_managed_conflict_failure_happens_before_branch_mutation(tmp_path, capsys):
    target = clone_adopter_with_remote(tmp_path)
    scripts = target / "scripts"
    scripts.mkdir()
    (scripts / "ai_common.py").write_text("KEEP-COMMON\n", encoding="utf-8")
    assert run(target, "git", "add", "scripts/ai_common.py").returncode == 0
    assert run(target, "git", "commit", "-qm", "conflicting managed file").returncode == 0
    before_commit, before_branch = current_head(target)

    installer = Installer(
        source=ROOT,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )
    assert installer.install() == 2
    error = capsys.readouterr().err
    assert "managed file conflicts detected" in error
    assert (current_head(target)) == (before_commit, before_branch)
    assert not adoption_branch_exists(target)
    assert (scripts / "ai_common.py").read_text(encoding="utf-8") == "KEEP-COMMON\n"


def worktree_files(target: Path) -> list[str]:
    return sorted(
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file() and ".git" not in path.parts
    )


def test_runtime_failure_restores_original_branch_and_filesystem(tmp_path, monkeypatch):
    target = clone_adopter_with_remote(tmp_path)
    before_commit, before_branch = current_head(target)
    installer = Installer(
        source=ROOT,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )
    monkeypatch.setattr(
        installer,
        "validate_managed_installation",
        lambda: (_ for _ in ()).throw(RuntimeError("simulated adoption runtime failure")),
    )

    assert installer.install() == 2
    assert (current_head(target)) == (before_commit, before_branch)
    assert not adoption_branch_exists(target)
    assert worktree_files(target) == ["README.md"]


def test_runtime_failure_restores_detached_head(tmp_path, monkeypatch):
    target = clone_adopter_with_remote(tmp_path)
    assert run(target, "git", "switch", "--detach", "HEAD").returncode == 0
    before_commit, before_branch = current_head(target)
    assert before_branch is None
    installer = Installer(
        source=ROOT,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )
    monkeypatch.setattr(
        installer,
        "validate_managed_installation",
        lambda: (_ for _ in ()).throw(RuntimeError("simulated detached failure")),
    )

    assert installer.install() == 2
    after_commit, after_branch = current_head(target)
    assert after_commit == before_commit
    assert after_branch is None
    assert not adoption_branch_exists(target)


def test_adoption_requires_clean_committed_repository(tmp_path):
    assert run(tmp_path, "git", "init", "-q").returncode == 0
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )
    assert installer.install() == 2
    assert not (tmp_path / ".ai").exists()


def test_adoption_preflight_warnings_list_tracked_hygiene_without_writing(tmp_path):
    assert run(tmp_path, "git", "init", "-q").returncode == 0
    assert run(tmp_path, "git", "config", "user.email", "test@example.invalid").returncode == 0
    assert run(tmp_path, "git", "config", "user.name", "Test").returncode == 0
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    (tmp_path / ".DS_Store").write_text("noise\n", encoding="utf-8")
    assert run(tmp_path, "git", "add", "README.md").returncode == 0
    assert run(tmp_path, "git", "add", "-f", ".DS_Store").returncode == 0
    assert run(tmp_path, "git", "commit", "-qm", "initial").returncode == 0

    warnings = adoption_preflight_warnings(tmp_path)

    assert any("Tracked files commonly ignored locally" in item for item in warnings)
    assert not any("dirty" in item.lower() for item in warnings)


def test_adoption_install_excludes_template_release_manifest(tmp_path):
    """採用インストール後の採用者ツリーにテンプレートのリリースマニフェストが含まれないことを確認する。"""
    assert run(tmp_path, "git", "init", "-q").returncode == 0
    assert run(tmp_path, "git", "config", "user.email", "test@example.invalid").returncode == 0
    assert run(tmp_path, "git", "config", "user.name", "Test").returncode == 0
    (tmp_path / "README.md").write_text("# Adopter project\n", encoding="utf-8")
    assert run(tmp_path, "git", "add", "README.md").returncode == 0
    assert run(tmp_path, "git", "commit", "-qm", "initial").returncode == 0

    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )
    assert installer.install() == 0

    # テンプレートのリリースアーティファクトダイジェストは採用者ツリーに含まれてはならない。
    # このファイルは採用者ツリーに存在しないアーティファクトの整合性を主張するスタールなマニフェストになる。
    assert not (tmp_path / ".ai" / "cockpit" / "release-digests.json").exists()
    # その他のテンプレートサプライチェーン証拠ファイルも同様に除外されていることを確認する。
    assert not (tmp_path / ".ai" / "cockpit" / "sbom.json").exists()
    assert not (tmp_path / ".ai" / "cockpit" / "provenance.json").exists()
    assert not (tmp_path / ".ai" / "cockpit" / "bandit_low_risk_baseline.json").exists()
