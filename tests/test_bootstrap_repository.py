import subprocess

import pytest

from bootstrap_repository import BootstrapRepositoryError, detect_repository, revalidate_repository


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


def initialized_repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(tmp_path, "add", "tracked.txt")
    git(tmp_path, "commit", "-qm", "initial")
    return tmp_path


def test_detector_rejects_non_git_and_no_commit_paths(tmp_path):
    with pytest.raises(BootstrapRepositoryError, match="not a Git repository"):
        detect_repository(tmp_path)

    git(tmp_path, "init", "-q")
    with pytest.raises(BootstrapRepositoryError, match="no commit"):
        detect_repository(tmp_path)


def test_detector_captures_clean_facts_and_installed_presence(tmp_path):
    root = initialized_repo(tmp_path)
    (root / ".ai" / "cockpit").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "scripts" / "ai_start.py").write_text("# runtime\n", encoding="utf-8")
    git(root, "add", ".ai", "scripts")
    git(root, "commit", "-qm", "install runtime")

    snapshot = detect_repository(root)

    assert snapshot.root == root.resolve()
    assert len(snapshot.commit) == 40
    assert snapshot.branch == "master" or snapshot.branch == "main"
    assert snapshot.detached is False
    assert snapshot.dirty_paths == ()
    assert snapshot.conflict_paths == ()
    assert snapshot.installed_cockpit is True
    assert snapshot.remote_head is None


def test_detector_captures_dirty_untracked_and_detached_state(tmp_path):
    root = initialized_repo(tmp_path)
    (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (root / "new.txt").write_text("new\n", encoding="utf-8")
    snapshot = detect_repository(root)
    assert "tracked.txt" in snapshot.unstaged_paths
    assert "new.txt" in snapshot.untracked_paths
    assert set(snapshot.dirty_paths) == {"tracked.txt", "new.txt"}

    git(root, "switch", "--detach", "-q", "HEAD")
    detached = detect_repository(root)
    assert detached.detached is True
    assert detached.branch is None


def test_detector_records_remote_urls_and_symbolic_head(tmp_path):
    root = initialized_repo(tmp_path)
    git(root, "remote", "add", "origin", "https://example.invalid/source.git")
    git(root, "remote", "set-url", "--push", "origin", "ssh://example.invalid/source.git")

    snapshot = detect_repository(root)

    assert snapshot.remotes["origin"].fetch_url == "https://example.invalid/source.git"
    assert snapshot.remotes["origin"].push_url == "ssh://example.invalid/source.git"
    assert snapshot.local_branches
    assert isinstance(snapshot.remote_branches, tuple)


def test_detector_records_unmerged_conflict_paths(tmp_path):
    root = initialized_repo(tmp_path)
    git(root, "switch", "-qc", "other")
    (root / "tracked.txt").write_text("other\n", encoding="utf-8")
    git(root, "commit", "-qam", "other change")
    git(root, "switch", "-q", "-")
    (root / "tracked.txt").write_text("main\n", encoding="utf-8")
    git(root, "commit", "-qam", "main change")
    subprocess.run(["git", "merge", "other"], cwd=root, text=True, capture_output=True, check=False)

    snapshot = detect_repository(root)
    assert snapshot.conflict_paths == ("tracked.txt",)


def test_revalidate_returns_all_mismatches_and_never_writes(tmp_path):
    root = initialized_repo(tmp_path)
    confirmed = detect_repository(root, bootstrap_base_commit="base-commit")
    (root / "new.txt").write_text("drift\n", encoding="utf-8")

    report = revalidate_repository(confirmed)

    assert report.ok is False
    assert "dirty_paths" in report.mismatches
    assert report.mismatches["dirty_paths"]["expected"] == []
    assert (root / "new.txt").exists()


def test_revalidate_detects_changed_base_commit(tmp_path):
    root = initialized_repo(tmp_path)
    confirmed = detect_repository(root, bootstrap_base_commit="base-1")
    current = detect_repository(root, bootstrap_base_commit="base-2")

    report = revalidate_repository(confirmed, current=current)

    assert report.ok is False
    assert "bootstrap_base_commit" in report.mismatches
