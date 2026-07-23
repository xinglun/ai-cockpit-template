import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

import scripts.check_release_preflight as preflight
import scripts.finalize_release_freeze as finalizer
from scripts.check_release_preflight import ReleasePreflightError
from scripts.check_release_preflight import _load_object
from scripts.check_release_preflight import canonical_archive_sha
from scripts.check_release_preflight import resolve_source_commit
from scripts.check_release_preflight import validate_release_preflight


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


def test_canonical_archive_builder_returns_sha256_for_repository():
    digest = canonical_archive_sha(Path.cwd(), "HEAD")
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


def test_normalized_source_tree_identity_is_stable():
    digest = preflight.canonical_source_tree(Path.cwd(), "HEAD")
    assert len(digest) == 64
    assert digest == preflight.canonical_source_tree(Path.cwd(), "HEAD")


def test_source_ref_resolves_symbolic_head_to_a_concrete_commit():
    resolved = resolve_source_commit(Path.cwd(), "HEAD")
    assert len(resolved) == 40
    assert resolved == resolve_source_commit(Path.cwd(), resolved)


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


def test_finalize_release_freeze_writes_post_close_lifecycle_evidence(monkeypatch, tmp_path):
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    (tmp_path / ".ai" / "work-items" / "active").mkdir(parents=True)
    (tmp_path / ".ai" / "cockpit" / "current_status.md").write_text(
        "- State: `no_active_work_item`\n", encoding="utf-8"
    )
    (tmp_path / ".ai" / "cockpit" / "release-freeze.json").write_text(
        '{"state":"candidate"}\n', encoding="utf-8"
    )
    (tmp_path / "release.json").write_text(
        '{"releaseArchive":{"sha256":"old"}}\n', encoding="utf-8"
    )
    (tmp_path / "release-state.json").write_text(
        '{"metadataDigests":{"published":"old","candidate":"candidate"}}\n',
        encoding="utf-8",
    )
    (tmp_path / ".ai" / "cockpit" / "release-digests.json").write_text(
        '{"format":"ai-cockpit-release-digests","version":1,"sourceCommit":"old",'
        '"releaseTag":"v0.5.39","artifacts":{"release.json":"old"}}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(finalizer, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        finalizer, "discover_remote_default_candidates", lambda _run: [("origin", "main")]
    )

    def fake_git(args):
        outputs = {
            ("branch", "--show-current"): "main\n",
            ("status", "--porcelain", "--untracked-files=all"): "",
            ("rev-parse", "HEAD"): "commit\n",
            ("rev-parse", "origin/main"): "commit\n",
        }
        return SimpleNamespace(returncode=0, stdout=outputs.get(tuple(args), ""), stderr="")

    monkeypatch.setattr(finalizer, "run_git", fake_git)
    monkeypatch.setattr(finalizer, "canonical_source_tree", lambda _root, _commit: "tree")
    monkeypatch.setattr(finalizer, "canonical_archive_sha", lambda _root, _commit: "archive")

    assert finalizer.main() == 0
    freeze = json.loads((tmp_path / ".ai" / "cockpit" / "release-freeze.json").read_text())
    assert freeze["lifecycle"]["state"] == "closed_and_synchronized"
    assert freeze["lifecycle"]["command"] == "make ai-close-work-item"
    assert (
        json.loads((tmp_path / "release.json").read_text())["releaseArchive"]["sha256"] == "archive"
    )
    release_state = json.loads((tmp_path / "release-state.json").read_text())
    assert (
        release_state["metadataDigests"]["published"]
        == hashlib.sha256((tmp_path / "release.json").read_bytes()).hexdigest()
    )
    release_digests = json.loads(
        (tmp_path / ".ai" / "cockpit" / "release-digests.json").read_text()
    )
    assert release_digests["sourceCommit"] == "HEAD"
    assert (
        release_digests["artifacts"]["release.json"]
        == hashlib.sha256((tmp_path / "release.json").read_bytes()).hexdigest()
    )


def test_finalize_release_freeze_fails_closed_on_malformed_release_state(monkeypatch, tmp_path):
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    (tmp_path / ".ai" / "work-items" / "active").mkdir(parents=True)
    (tmp_path / ".ai" / "cockpit" / "current_status.md").write_text(
        "- State: `no_active_work_item`\n", encoding="utf-8"
    )
    (tmp_path / ".ai" / "cockpit" / "release-freeze.json").write_text("{}\n")
    (tmp_path / ".ai" / "cockpit" / "release-digests.json").write_text("{}\n")
    (tmp_path / "release.json").write_text("{}\n")
    (tmp_path / "release-state.json").write_text("[]\n")
    monkeypatch.setattr(finalizer, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        finalizer, "discover_remote_default_candidates", lambda _run: [("origin", "main")]
    )

    def fake_git(args):
        outputs = {
            ("branch", "--show-current"): "main\n",
            ("status", "--porcelain", "--untracked-files=all"): "",
            ("rev-parse", "HEAD"): "commit\n",
            ("rev-parse", "origin/main"): "commit\n",
        }
        return SimpleNamespace(returncode=0, stdout=outputs.get(tuple(args), ""), stderr="")

    monkeypatch.setattr(finalizer, "run_git", fake_git)
    monkeypatch.setattr(finalizer, "canonical_source_tree", lambda _root, _commit: "tree")
    monkeypatch.setattr(finalizer, "canonical_archive_sha", lambda _root, _commit: "archive")
    assert finalizer.main() == 1


def test_finalize_release_freeze_candidate_mode_binds_to_work_item_branch(monkeypatch, tmp_path):
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    (active / "task.contract.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / ".ai" / "cockpit" / "release-freeze.json").write_text(
        '{"state":"candidate"}\n', encoding="utf-8"
    )
    (tmp_path / ".ai" / "cockpit" / "release-digests.json").write_text(
        '{"sourceCommit":"old","artifacts":{}}\n', encoding="utf-8"
    )
    (tmp_path / "release.json").write_text(
        '{"releaseTag":"v0.5.39","releaseArchive":{"sha256":"old"}}\n',
        encoding="utf-8",
    )
    (tmp_path / "release-state.json").write_text(
        '{"metadataDigests":{"published":"old"}}\n', encoding="utf-8"
    )
    monkeypatch.setattr(finalizer, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        finalizer, "discover_remote_default_candidates", lambda _run: [("origin", "main")]
    )

    def fake_git(args):
        outputs = {
            ("branch", "--show-current"): "codex/task\n",
            ("status", "--porcelain", "--untracked-files=all"): "",
            ("rev-parse", "HEAD"): "candidate-commit\n",
            ("rev-parse", "origin/main"): "default-commit\n",
        }
        return SimpleNamespace(returncode=0, stdout=outputs.get(tuple(args), ""), stderr="")

    monkeypatch.setattr(finalizer, "run_git", fake_git)
    monkeypatch.setattr(finalizer, "canonical_source_tree", lambda _root, _commit: "tree")
    monkeypatch.setattr(finalizer, "canonical_archive_sha", lambda _root, _commit: "archive")

    assert finalizer.main(candidate_task="task") == 0
    freeze = json.loads((tmp_path / ".ai" / "cockpit" / "release-freeze.json").read_text())
    assert freeze["lifecycle"]["state"] == "candidate_prepared"
    assert freeze["lifecycle"]["candidateBranch"] == "codex/task"
    assert freeze["lifecycle"]["defaultBranch"] == "main"


def test_finalize_release_freeze_premerge_requires_archived_work_item(monkeypatch, tmp_path):
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    (tmp_path / ".ai" / "cockpit" / "current_status.md").write_text(
        "- State: `no_active_work_item`\n", encoding="utf-8"
    )
    (tmp_path / ".ai" / "cockpit" / "release-freeze.json").write_text(
        '{"state":"candidate"}\n', encoding="utf-8"
    )
    (tmp_path / ".ai" / "cockpit" / "release-digests.json").write_text(
        '{"sourceCommit":"old","artifacts":{}}\n', encoding="utf-8"
    )
    (tmp_path / "release.json").write_text(
        '{"releaseArchive":{"sha256":"old"}}\n', encoding="utf-8"
    )
    (tmp_path / "release-state.json").write_text(
        '{"metadataDigests":{"published":"old"}}\n', encoding="utf-8"
    )
    monkeypatch.setattr(finalizer, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        finalizer, "discover_remote_default_candidates", lambda _run: [("origin", "main")]
    )

    def fake_git(args):
        outputs = {
            ("branch", "--show-current"): "codex/task\n",
            ("status", "--porcelain", "--untracked-files=all"): "",
            ("rev-parse", "HEAD"): "commit\n",
            ("rev-parse", "origin/main"): "old-commit\n",
        }
        return SimpleNamespace(returncode=0, stdout=outputs.get(tuple(args), ""), stderr="")

    monkeypatch.setattr(finalizer, "run_git", fake_git)
    monkeypatch.setattr(finalizer, "canonical_source_tree", lambda _root, _commit: "tree")
    monkeypatch.setattr(finalizer, "canonical_archive_sha", lambda _root, _commit: "archive")

    assert finalizer.main(premerge_task="task") == 1
    (archive / "task.contract.json").write_text("{}\n", encoding="utf-8")
    assert finalizer.main(premerge_task="task") == 0
    freeze = json.loads((tmp_path / ".ai" / "cockpit" / "release-freeze.json").read_text())
    assert freeze["lifecycle"]["state"] == "premerge_finalized"
    assert freeze["lifecycle"]["command"] == "make finalize-release-freeze-premerge TASK=task"


def test_main_accepts_frozen_candidate(tmp_path, monkeypatch, capsys):
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    (tmp_path / ".ai" / "guards").mkdir(parents=True)
    (tmp_path / ".ai" / "work-items" / "active").mkdir(parents=True)
    (tmp_path / ".ai" / "work-items" / "archive").mkdir(parents=True)
    (tmp_path / "release.json").write_text('{"releaseArchive":{"sha256":"abc"}}', encoding="utf-8")
    (tmp_path / ".ai" / "cockpit" / "release-freeze.json").write_text(
        '{"state":"frozen","sourceTree":"tree","archiveSha256":"abc",'
        '"lifecycle":{"state":"closed_and_synchronized",'
        '"command":"make ai-close-work-item","baseCommit":"tree",'
        '"worktreeClean":true}}',
        encoding="utf-8",
    )
    (tmp_path / ".ai" / "cockpit" / "release-digests.json").write_text(
        '{"sourceCommit":"HEAD"}', encoding="utf-8"
    )
    (tmp_path / ".ai" / "guards" / "governance_complexity_policy.yaml").write_text(
        "archiveGrowth: 10\n", encoding="utf-8"
    )
    monkeypatch.setattr(preflight, "canonical_archive_sha", lambda root, commit: "abc")
    monkeypatch.setattr(preflight, "canonical_source_tree", lambda root, commit: "tree")
    monkeypatch.setattr(preflight, "resolve_source_commit", lambda root, ref: "commit")
    monkeypatch.setattr(
        "sys.argv",
        ["check_release_preflight", "--root", str(tmp_path), "--source-commit", "HEAD"],
    )
    assert preflight.main() == 0
    assert "release preflight passed" in capsys.readouterr().out
