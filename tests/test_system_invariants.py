import json
import shutil
from pathlib import Path

import pytest

import check_system_invariants
from check_system_invariants import release_contract_issues


ROOT = Path(__file__).resolve().parents[1]


def write_release_contract_fixture(root, target="quality"):
    (root / "docs" / "getting-started").mkdir(parents=True)
    metadata = {"publicContract": {"projectQualityTarget": target}}
    (root / "release.json").write_text(json.dumps(metadata), encoding="utf-8")
    marker = f"<!-- public-quality-target: {target} -->\n"
    for name in ("README.md", "README.ja.md", "README.zh-CN.md"):
        (root / name).write_text(marker, encoding="utf-8")
    (root / "docs" / "getting-started" / "installation.md").write_text(marker, encoding="utf-8")
    return metadata


def _archive_summary_version_issues(issues):
    return [
        issue
        for issue in issues
        if "archived Summary summaryVersion must be absent or 1/2 when present" in issue
    ]


def _copy_repository_tree(tmp_path):
    copy = tmp_path / "repository"
    shutil.copytree(
        ROOT, copy, ignore=shutil.ignore_patterns(".git", ".venv", "target", "__pycache__")
    )
    return copy


def test_release_contract_accepts_consistent_public_quality_target(tmp_path):
    metadata = write_release_contract_fixture(tmp_path)
    assert release_contract_issues(tmp_path, metadata) == []


def test_release_contract_rejects_documentation_drift(tmp_path):
    metadata = write_release_contract_fixture(tmp_path)
    (tmp_path / "README.ja.md").write_text(
        "<!-- public-quality-target: stale -->\n", encoding="utf-8"
    )
    assert release_contract_issues(tmp_path, metadata) == [
        "README.ja.md: public quality target differs from release.json"
    ]


def test_release_contract_rejects_invalid_target(tmp_path):
    metadata = write_release_contract_fixture(tmp_path, target="quality; rm -rf")
    assert release_contract_issues(tmp_path, metadata) == [
        "release.json public project quality target is missing or invalid"
    ]


@pytest.mark.parametrize("summary_version", [None, 1])
def test_system_invariants_allow_legacy_archive_summary_versions(
    tmp_path, monkeypatch, summary_version
):
    copy = _copy_repository_tree(tmp_path)
    archive_summary = next((copy / ".ai" / "work-items" / "archive").rglob("*.summary.json"))
    data = json.loads(archive_summary.read_text(encoding="utf-8"))
    if summary_version is None:
        data.pop("summaryVersion", None)
    else:
        data["summaryVersion"] = summary_version
    archive_summary.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        check_system_invariants, "exercise_installer", lambda *_args, **_kwargs: None
    )
    issues = check_system_invariants.invariant_issues(copy)
    assert _archive_summary_version_issues(issues) == []


def test_system_invariants_reject_archive_summary_invalid_version(tmp_path, monkeypatch):
    copy = _copy_repository_tree(tmp_path)
    archive_summary = next((copy / ".ai" / "work-items" / "archive").rglob("*.summary.json"))
    data = json.loads(archive_summary.read_text(encoding="utf-8"))
    data["summaryVersion"] = 3
    archive_summary.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        check_system_invariants, "exercise_installer", lambda *_args, **_kwargs: None
    )
    issues = check_system_invariants.invariant_issues(copy)
    assert _archive_summary_version_issues(issues) == [
        f"{archive_summary.relative_to(copy)}: archived Summary summaryVersion must be absent or 1/2 when present"
    ]
