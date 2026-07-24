import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

import scripts.check_release_preflight as preflight
import scripts.finalize_release_freeze as finalizer
from scripts.check_release_preflight import ReleasePreflightError
from scripts.check_release_preflight import _load_object
from scripts.check_release_preflight import canonical_archive_sha
from scripts.check_release_preflight import resolve_source_commit
from scripts.check_release_preflight import resolve_release_identity_ref
from scripts.check_release_preflight import validate_release_preflight
from scripts.check_release_preflight import validate_release_identity
from scripts.check_release_preflight import validate_release_projection
from scripts.release_archive import canonical_archive_sha as deterministic_archive_sha
from scripts.release_archive import canonical_source_tree as deterministic_source_tree


def _fixture(**overrides):
    values = {
        "release": {"releaseArchive": {"sha256": "abc"}},
        "release_digests": {"sourceCommit": "HEAD"},
        "source_commit": "HEAD",
        "freeze": {
            "state": "frozen",
            "sourceTree": "tree",
            "archiveSha256": "abc",
            "lifecycle": {
                "state": "closed_and_synchronized",
                "command": "make ai-close-work-item",
                "baseCommit": "tree",
                "worktreeClean": True,
            },
        },
        "actual_archive_sha": "abc",
        "source_tree": "tree",
        "active_work_items": [],
        "archive_count": 10,
        "archive_max": 10,
    }
    values.update(overrides)
    return values


def test_release_preflight_accepts_frozen_source_bound_candidate():
    assert validate_release_preflight(**_fixture()) == []


def test_release_preflight_rejects_missing_malformed_or_mismatched_installer_digest():
    installer_sha = hashlib.sha256(b"installer\n").hexdigest()

    assert preflight.validate_installer_digest({}, installer_sha) == [
        "release.json installerDigest is missing or invalid"
    ]
    assert preflight.validate_installer_digest({"installerDigest": "bad"}, installer_sha) == [
        "release.json installerDigest is missing or invalid"
    ]
    assert preflight.validate_installer_digest(
        {"installerDigest": "0" * 64}, installer_sha
    ) == ["release.json installerDigest does not match source install.sh"]
    assert (
        preflight.validate_installer_digest(
            {"installerDigest": installer_sha}, installer_sha
        )
        == []
    )


def test_release_preflight_blocks_active_work_item_and_stale_digest():
    issues = validate_release_preflight(
        **_fixture(active_work_items=["task"], actual_archive_sha="new")
    )
    assert any("active Work Items" in issue for issue in issues)
    assert any("releaseArchive.sha256" in issue for issue in issues)
    assert any("release freeze archiveSha256" in issue for issue in issues)


def test_release_preflight_blocks_archive_budget_overflow_and_unfrozen_state():
    issues = validate_release_preflight(**_fixture(freeze={"state": "candidate"}, archive_count=11))
    assert any("archiveGrowth=11" in issue for issue in issues)
    assert any("state must be frozen" in issue for issue in issues)


def test_release_preflight_warns_on_archive_growth_when_policy_is_warning_only():
    assert (
        validate_release_preflight(
            **_fixture(archive_count=538, archive_max=200, archive_enforcement="warning")
        )
        == []
    )


def test_release_preflight_blocks_source_tree_mismatch():
    issues = validate_release_preflight(**_fixture(source_tree="different-tree"))
    assert any("sourceTree" in issue for issue in issues)


def test_release_preflight_blocks_freeze_created_before_close():
    freeze = _fixture()["freeze"]
    del freeze["lifecycle"]
    issues = validate_release_preflight(**_fixture(freeze=freeze))
    assert any("finalized after Work Item archive" in issue for issue in issues)


def test_release_preflight_accepts_archive_bound_premerge_freeze():
    freeze = _fixture()["freeze"]
    freeze["lifecycle"] = {
        "state": "premerge_finalized",
        "command": "make finalize-release-freeze-premerge TASK=task",
        "baseCommit": "tree",
        "worktreeClean": True,
    }
    assert validate_release_preflight(**_fixture(freeze=freeze)) == []


def test_release_preflight_blocks_stale_digest_source_commit():
    issues = validate_release_preflight(**_fixture(release_digests={"sourceCommit": "old"}))
    assert any("release-digests sourceCommit" in issue for issue in issues)


def test_release_preflight_accepts_matching_digest_source_commit():
    assert validate_release_preflight(**_fixture(release_digests={"sourceCommit": "HEAD"})) == []


def _identity_fixture(**overrides):
    values = {
        "release": {"releaseTag": "v0.5.39"},
        "freeze": {
            "sourceCommit": "a" * 40,
            "tagTarget": "a" * 40,
            "metadataCommit": "b" * 40,
            "releaseTag": "v0.5.39",
        },
        "release_digests": {
            "sourceCommit": "a" * 40,
            "tagTarget": "a" * 40,
            "metadataCommit": "b" * 40,
            "releaseTag": "v0.5.39",
        },
        "source_commit": "a" * 40,
        "tag_target": "a" * 40,
        "metadata_commit": "b" * 40,
    }
    values.update(overrides)
    return values


def test_release_preflight_rejects_symbolic_or_stale_source_identity():
    issues = validate_release_identity(
        **_identity_fixture(release_digests={"sourceCommit": "HEAD"})
    )
    assert any("sourceCommit" in issue and "concrete" in issue for issue in issues)


def test_release_preflight_rejects_metadata_commit_drift():
    issues = validate_release_identity(
        **_identity_fixture(
            freeze={
                "sourceCommit": "a" * 40,
                "tagTarget": "a" * 40,
                "metadataCommit": "c" * 40,
                "releaseTag": "v0.5.39",
            }
        )
    )
    assert any("metadataCommit" in issue for issue in issues)


def test_release_preflight_accepts_source_bound_finalized_candidate():
    assert validate_release_identity(**_identity_fixture()) == []


def _projection_fixture(**overrides):
    values = {
        "state": {
            "state": "candidate_prepared",
            "releaseTag": "v0.5.34",
            "previousRelease": "v0.5.33",
        },
        "release": {"releaseTag": "v0.5.33"},
        "candidate": {
            "releaseTag": "v0.5.34",
            "basedOnReleaseTag": "v0.5.33",
        },
    }
    values.update(overrides)
    return values


def test_release_projection_accepts_canonical_candidate_lineage():
    assert validate_release_projection(**_projection_fixture()) == []


def test_release_projection_rejects_mixed_candidate_lineage_before_archive_generation():
    issues = validate_release_projection(
        **_projection_fixture(
            state={
                "state": "candidate_prepared",
                "releaseTag": "v0.5.40",
                "previousRelease": "v0.5.39",
            }
        )
    )
    assert any("candidate releaseTag" in issue for issue in issues)
    assert any("previousRelease" in issue for issue in issues)


def test_release_projection_rejects_candidate_that_does_not_derive_from_published_release():
    issues = validate_release_projection(
        **_projection_fixture(candidate={"releaseTag": "v0.5.34", "basedOnReleaseTag": "v0.5.32"})
    )
    assert any("basedOnReleaseTag" in issue for issue in issues)


def test_canonical_archive_builder_returns_sha256_for_repository():
    digest = canonical_archive_sha(Path.cwd(), "HEAD")
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


def test_deterministic_archive_matches_in_fresh_detached_repository(tmp_path):
    source_root = Path.cwd()
    source = resolve_source_commit(source_root, "HEAD")
    repo = tmp_path / "fresh-archive-repository"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", str(source_root)], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "fetch", "-q", "origin", f"{source}:refs/remotes/origin/main"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "checkout", "--detach", "-q", source], check=True)
    assert deterministic_source_tree(repo, source) == deterministic_source_tree(source_root, source)
    assert deterministic_archive_sha(repo, source) == deterministic_archive_sha(source_root, source)


def test_normalized_source_tree_identity_is_stable():
    digest = preflight.canonical_source_tree(Path.cwd(), "HEAD")
    assert len(digest) == 64
    assert digest == preflight.canonical_source_tree(Path.cwd(), "HEAD")


def test_work_item_active_and_archive_evidence_are_excluded_from_release_source_tree():
    attributes = (Path.cwd() / ".gitattributes").read_text(encoding="utf-8")
    assert ".ai/work-items/active export-ignore" in attributes
    assert ".ai/work-items/archive export-ignore" in attributes


def test_source_ref_resolves_symbolic_head_to_a_concrete_commit():
    resolved = resolve_source_commit(Path.cwd(), "HEAD")
    assert len(resolved) == 40
    assert resolved == resolve_source_commit(Path.cwd(), resolved)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _run_release_preflight(repo: Path, source_ref: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "check_release_preflight.py"),
            "--root",
            str(repo),
            "--source-commit",
            source_ref,
        ],
        check=False,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
    )


def _build_candidate_merge(tmp_path: Path) -> tuple[Path, Path, str]:
    source_root = Path.cwd()
    repo = tmp_path / "source"
    remote = tmp_path / "origin.git"
    fresh = tmp_path / "fresh"
    repo.mkdir()
    for relative in (
        "ai_common.py",
        "finalize_release_freeze.py",
        "check_release_preflight.py",
        "release_archive.py",
    ):
        target = repo / "scripts" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / "scripts" / relative, target)
    (repo / "scripts" / "check_supply_chain.py").write_text(
        "import hashlib\n\n"
        "def sha256_text(value: str) -> str:\n"
        "    return hashlib.sha256(value.encode()).hexdigest()\n",
        encoding="utf-8",
    )
    (repo / ".gitattributes").write_text(
        "release.json export-ignore\n"
        "next-release.json export-ignore\n"
        "release-state.json export-ignore\n"
        ".ai/cockpit/release-digests.json export-ignore\n"
        ".ai/cockpit/release-freeze.json export-ignore\n"
        ".ai/work-items/archive export-ignore\n"
        ".ai/work-items/active export-ignore\n"
        ".ai/cockpit/current_status.md export-ignore\n",
        encoding="utf-8",
    )
    (repo / "source.txt").write_text("base\n", encoding="utf-8")
    (repo / "install.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    installer_digest = hashlib.sha256((repo / "install.sh").read_bytes()).hexdigest()
    (repo / ".ai" / "cockpit").mkdir(parents=True)
    (repo / ".ai" / "cockpit" / "current_status.md").write_text(
        "- State: `no_active_work_item`\n", encoding="utf-8"
    )
    _write_json(repo / ".ai" / "cockpit" / "release-freeze.json", {"state": "candidate"})
    _write_json(
        repo / ".ai" / "cockpit" / "release-digests.json",
        {"sourceCommit": "old", "artifacts": {}},
    )
    _write_json(
        repo / "release.json",
        {
            "releaseTag": "v0.5.39",
            "installerDigest": installer_digest,
            "releaseArchive": {"sha256": "old"},
        },
    )
    _write_json(
        repo / "next-release.json",
        {"releaseTag": "v0.5.40", "basedOnReleaseTag": "v0.5.39"},
    )
    _write_json(
        repo / "release-state.json",
        {
            "state": "candidate_prepared",
            "releaseTag": "v0.5.40",
            "previousRelease": "v0.5.39",
            "metadataDigests": {"published": "old"},
        },
    )
    policy = repo / ".ai" / "guards" / "governance_complexity_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        "max:\n  archiveGrowth: 538\nenforcement:\n  archiveGrowth: warning\n",
        encoding="utf-8",
    )
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Release Test")
    _git(repo, "config", "user.email", "release-test@example.invalid")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(
        ["git", "--git-dir", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"],
        check=True,
    )
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")
    _git(repo, "remote", "set-head", "origin", "main")
    _git(repo, "switch", "-q", "-c", "candidate")
    (repo / "source.txt").write_text("candidate\n", encoding="utf-8")
    contract = repo / ".ai" / "work-items" / "archive" / "2026" / "task.contract.json"
    _write_json(
        contract,
        {
            "scope": [
                "release.json",
                "release-state.json",
                ".ai/cockpit/release-freeze.json",
                ".ai/cockpit/release-digests.json",
            ]
        },
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "candidate")
    subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "finalize_release_freeze.py"),
            "--premerge-task",
            "task",
            "--source-commit",
            "origin/main",
            "--tag-target",
            "origin/main",
            "--metadata-commit",
            "origin/main",
        ],
        cwd=repo,
        check=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "freeze candidate")
    _git(repo, "switch", "-q", "main")
    _git(repo, "merge", "-q", "--no-ff", "candidate", "-m", "merge candidate")
    merge_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "-q", "origin", "main")
    _git(fresh.parent, "init", "-q", str(fresh))
    _git(fresh, "remote", "add", "origin", str(remote))
    _git(fresh, "fetch", "-q", "origin", "main:refs/remotes/origin/main")
    _git(fresh, "checkout", "--detach", "-q", merge_commit)
    return repo, fresh, merge_commit


def test_candidate_freeze_survives_real_no_ff_merge_and_detached_preflight(tmp_path):
    _, fresh, merge_commit = _build_candidate_merge(tmp_path)
    result = _run_release_preflight(fresh, "origin/main")
    assert result.returncode == 0, result.stderr
    assert f"source={merge_commit}" in result.stdout
    assert "release preflight passed" in result.stdout


def test_postmerge_preflight_rejects_included_content_after_candidate_merge(tmp_path):
    repo, fresh, _ = _build_candidate_merge(tmp_path)
    (repo / "source.txt").write_text("post-merge drift\n", encoding="utf-8")
    _git(repo, "add", "source.txt")
    _git(repo, "commit", "-q", "-m", "drift after merge")
    drift_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "-q", "origin", "main")
    _git(fresh, "fetch", "-q", "origin", "main:refs/remotes/origin/main")
    _git(fresh, "checkout", "--detach", "-q", drift_commit)
    result = _run_release_preflight(fresh, "origin/main")
    assert result.returncode == 1
    assert "release preflight blocked" in result.stderr
    assert "archiveSha256 does not match regenerated archive" in result.stderr


def test_release_identity_ref_resolves_controlled_origin_ref():
    resolved = resolve_release_identity_ref(Path.cwd(), "origin/main", "tagTarget")
    assert len(resolved) == 40


def test_release_identity_ref_rejects_head():
    with pytest.raises(ReleasePreflightError, match="concrete SHA or controlled origin ref"):
        resolve_release_identity_ref(Path.cwd(), "HEAD", "metadataCommit")


def test_load_object_rejects_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ReleasePreflightError, match="must be a JSON object"):
        _load_object(path, "fixture")


def test_load_object_rejects_malformed_json(tmp_path):
    path = tmp_path / "malformed.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ReleasePreflightError, match="missing or invalid"):
        _load_object(path, "fixture")


def test_finalize_release_freeze_requires_clean_synchronized_default_branch(monkeypatch, tmp_path):
    monkeypatch.setattr(finalizer, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(finalizer, "discover_remote_default_candidates", lambda _run: [])
    assert finalizer.main() == 1


def _configure_finalizer(
    monkeypatch,
    tmp_path: Path,
    *,
    branch: str = "main",
    head: str = "commit",
    remote_head: str = "commit",
    active_task: str | None = None,
    release_state: str = '{"metadataDigests":{"published":"old"}}\n',
) -> list[tuple[str, str]]:
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    if active_task is not None:
        (active / f"{active_task}.contract.json").write_text(
            '{"scope":["release.json","release-state.json",".ai/cockpit/release-freeze.json",'
            '".ai/cockpit/release-digests.json"]}\n',
            encoding="utf-8",
        )
    (tmp_path / ".ai" / "cockpit" / "current_status.md").write_text(
        "- State: `no_active_work_item`\n", encoding="utf-8"
    )
    (tmp_path / ".ai" / "cockpit" / "release-freeze.json").write_text(
        '{"state":"candidate"}\n', encoding="utf-8"
    )
    (tmp_path / ".ai" / "cockpit" / "release-digests.json").write_text(
        '{"format":"ai-cockpit-release-digests","version":1,"sourceCommit":"old",'
        '"releaseTag":"v0.5.39","artifacts":{"release.json":"old"}}\n',
        encoding="utf-8",
    )
    (tmp_path / "release.json").write_text(
        '{"releaseTag":"v0.5.39","installerDigest":"old",'
        '"releaseArchive":{"sha256":"old"}}\n',
        encoding="utf-8",
    )
    (tmp_path / "install.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (tmp_path / "release-state.json").write_text(release_state, encoding="utf-8")
    monkeypatch.setattr(finalizer, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        finalizer, "discover_remote_default_candidates", lambda _run: [("origin", "main")]
    )

    def fake_git(args):
        outputs = {
            ("branch", "--show-current"): f"{branch}\n",
            ("status", "--porcelain", "--untracked-files=all"): "",
            ("rev-parse", "HEAD"): f"{head}\n",
            ("rev-parse", "origin/main"): f"{remote_head}\n",
        }
        return SimpleNamespace(returncode=0, stdout=outputs.get(tuple(args), ""), stderr="")

    monkeypatch.setattr(finalizer, "run_git", fake_git)
    materialized = []
    monkeypatch.setattr(
        finalizer,
        "canonical_source_tree",
        lambda _root, commit: materialized.append(("tree", commit)) or "tree",
    )
    monkeypatch.setattr(
        finalizer,
        "canonical_archive_sha",
        lambda _root, commit: materialized.append(("archive", commit)) or "archive",
    )
    return materialized


def _archive_finalizer_task(tmp_path: Path) -> None:
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    (archive / "task.contract.json").write_text(
        '{"scope":["release.json","release-state.json",".ai/cockpit/release-freeze.json",'
        '".ai/cockpit/release-digests.json"]}\n',
        encoding="utf-8",
    )


def _finalize_premerge(source_identity: str) -> int:
    return finalizer.main(
        premerge_task="task",
        source_commit=source_identity,
        tag_target=source_identity,
        metadata_commit=source_identity,
    )


def test_finalize_release_freeze_writes_post_close_lifecycle_evidence(monkeypatch, tmp_path):
    _configure_finalizer(monkeypatch, tmp_path)

    assert (
        finalizer.main(
            source_commit="a" * 40,
            tag_target="a" * 40,
            metadata_commit="b" * 40,
        )
        == 0
    )
    freeze = json.loads((tmp_path / ".ai" / "cockpit" / "release-freeze.json").read_text())
    assert freeze["lifecycle"]["state"] == "closed_and_synchronized"
    assert freeze["lifecycle"]["command"] == "make ai-close-work-item"
    assert freeze["sourceCommit"] == "a" * 40
    assert freeze["tagTarget"] == "a" * 40
    assert freeze["metadataCommit"] == "b" * 40
    assert (
        json.loads((tmp_path / "release.json").read_text())["releaseArchive"]["sha256"] == "archive"
    )
    assert json.loads((tmp_path / "release.json").read_text())[
        "installerDigest"
    ] == hashlib.sha256((tmp_path / "install.sh").read_bytes()).hexdigest()
    release_state = json.loads((tmp_path / "release-state.json").read_text())
    assert (
        release_state["metadataDigests"]["published"]
        == hashlib.sha256((tmp_path / "release.json").read_bytes()).hexdigest()
    )
    release_digests = json.loads(
        (tmp_path / ".ai" / "cockpit" / "release-digests.json").read_text()
    )
    assert release_digests["sourceCommit"] == "a" * 40
    assert release_digests["tagTarget"] == "a" * 40
    assert release_digests["metadataCommit"] == "b" * 40
    assert (
        release_digests["artifacts"]["release.json"]
        == hashlib.sha256((tmp_path / "release.json").read_bytes()).hexdigest()
    )


def test_finalize_release_freeze_fails_closed_on_malformed_release_state(monkeypatch, tmp_path):
    _configure_finalizer(monkeypatch, tmp_path, release_state="[]\n")
    assert finalizer.main() == 1


def test_finalize_release_freeze_candidate_mode_binds_to_work_item_branch(monkeypatch, tmp_path):
    _configure_finalizer(
        monkeypatch,
        tmp_path,
        branch="codex/task",
        head="candidate-commit",
        remote_head="default-commit",
        active_task="task",
    )

    assert finalizer.main(candidate_task="task") == 0
    freeze = json.loads((tmp_path / ".ai" / "cockpit" / "release-freeze.json").read_text())
    assert freeze["lifecycle"]["state"] == "candidate_prepared"
    assert freeze["lifecycle"]["candidateBranch"] == "codex/task"
    assert freeze["lifecycle"]["defaultBranch"] == "main"


def test_finalize_release_freeze_premerge_requires_archived_work_item(monkeypatch, tmp_path):
    materialized = _configure_finalizer(
        monkeypatch,
        tmp_path,
        branch="codex/task",
        remote_head="old-commit",
    )

    assert _finalize_premerge("origin/main") == 1
    _archive_finalizer_task(tmp_path)
    assert _finalize_premerge("origin/main") == 0
    assert materialized == [("tree", "commit"), ("archive", "commit")]
    freeze = json.loads((tmp_path / ".ai" / "cockpit" / "release-freeze.json").read_text())
    assert freeze["lifecycle"]["state"] == "premerge_finalized"
    assert freeze["lifecycle"]["command"] == "make finalize-release-freeze-premerge TASK=task"


def test_finalize_release_freeze_premerge_rejects_unresolved_source_identity(monkeypatch, tmp_path):
    _archive_finalizer_task(tmp_path)
    materialized = _configure_finalizer(monkeypatch, tmp_path, branch="codex/task")
    release_before = (tmp_path / "release.json").read_bytes()

    assert _finalize_premerge("missing/ref") == 1
    assert materialized == []
    assert (tmp_path / "release.json").read_bytes() == release_before


def test_main_accepts_frozen_candidate(tmp_path, monkeypatch, capsys):
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    (tmp_path / ".ai" / "guards").mkdir(parents=True)
    (tmp_path / ".ai" / "work-items" / "active").mkdir(parents=True)
    (tmp_path / ".ai" / "work-items" / "archive").mkdir(parents=True)
    (tmp_path / "release.json").write_text(
        '{"releaseTag":"v0.5.39","installerDigest":"' + "c" * 64
        + '","releaseArchive":{"sha256":"abc"}}',
        encoding="utf-8",
    )
    (tmp_path / "next-release.json").write_text(
        '{"releaseTag":"v0.5.40","basedOnReleaseTag":"v0.5.39"}', encoding="utf-8"
    )
    (tmp_path / "release-state.json").write_text(
        '{"state":"candidate_prepared","releaseTag":"v0.5.40","previousRelease":"v0.5.39"}',
        encoding="utf-8",
    )
    (tmp_path / ".ai" / "cockpit" / "release-freeze.json").write_text(
        '{"state":"frozen","sourceTree":"tree","archiveSha256":"abc",'
        '"sourceCommit":"' + "a" * 40 + '","tagTarget":"' + "a" * 40 + '",'
        '"metadataCommit":"' + "b" * 40 + '","releaseTag":"v0.5.39",'
        '"lifecycle":{"state":"closed_and_synchronized",'
        '"command":"make ai-close-work-item","baseCommit":"tree",'
        '"worktreeClean":true}}',
        encoding="utf-8",
    )
    (tmp_path / ".ai" / "cockpit" / "release-digests.json").write_text(
        '{"sourceCommit":"' + "a" * 40 + '","tagTarget":"' + "a" * 40 + '",'
        '"metadataCommit":"' + "b" * 40 + '","releaseTag":"v0.5.39"}',
        encoding="utf-8",
    )
    (tmp_path / ".ai" / "guards" / "governance_complexity_policy.yaml").write_text(
        "archiveGrowth: 10\n", encoding="utf-8"
    )
    monkeypatch.setattr(preflight, "canonical_archive_sha", lambda root, commit: "abc")
    monkeypatch.setattr(preflight, "canonical_source_tree", lambda root, commit: "tree")
    monkeypatch.setattr(preflight, "resolve_source_commit", lambda root, ref: "a" * 40)
    monkeypatch.setattr(preflight, "source_file_sha256", lambda root, commit, path: "c" * 64)
    monkeypatch.setattr(
        "sys.argv",
        ["check_release_preflight", "--root", str(tmp_path), "--source-commit", "HEAD"],
    )
    assert preflight.main() == 0
    assert "release preflight passed" in capsys.readouterr().out
