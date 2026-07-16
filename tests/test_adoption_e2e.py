import json
import subprocess
import sys
from pathlib import Path

from install_ai_cockpit import Installer, adoption_preflight_warnings


ROOT = Path(__file__).resolve().parents[1]


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


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
