from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.check_release_preflight as preflight
from scripts.check_release_preflight import ReleasePreflightError
from scripts.check_release_preflight import _load_object
from scripts.check_release_preflight import canonical_archive_sha
from scripts.check_release_preflight import validate_release_preflight


def _fixture(**overrides):
    values = {
        "release": {"releaseArchive": {"sha256": "abc"}},
        "freeze": {"state": "frozen", "sourceTree": "tree", "archiveSha256": "abc"},
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


def test_canonical_archive_builder_returns_sha256_for_repository():
    digest = canonical_archive_sha(Path.cwd(), "HEAD")
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


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


def test_main_accepts_frozen_candidate(tmp_path, monkeypatch, capsys):
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    (tmp_path / ".ai" / "guards").mkdir(parents=True)
    (tmp_path / ".ai" / "work-items" / "active").mkdir(parents=True)
    (tmp_path / ".ai" / "work-items" / "archive").mkdir(parents=True)
    (tmp_path / "release.json").write_text(
        '{"releaseArchive":{"sha256":"abc"}}', encoding="utf-8"
    )
    (tmp_path / ".ai" / "cockpit" / "release-freeze.json").write_text(
        '{"state":"frozen","sourceTree":"tree","archiveSha256":"abc"}',
        encoding="utf-8",
    )
    (tmp_path / ".ai" / "guards" / "governance_complexity_policy.yaml").write_text(
        "archiveGrowth: 10\n", encoding="utf-8"
    )
    monkeypatch.setattr(preflight, "canonical_archive_sha", lambda root, commit: "abc")
    monkeypatch.setattr(
        preflight.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="tree\n"),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["check_release_preflight", "--root", str(tmp_path), "--source-commit", "HEAD"],
    )
    assert preflight.main() == 0
    assert "release preflight passed" in capsys.readouterr().out
