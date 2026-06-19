import json

from check_system_invariants import release_contract_issues


def write_release_contract_fixture(root, target="quality"):
    (root / "docs").mkdir()
    metadata = {"publicContract": {"projectQualityTarget": target}}
    (root / "release.json").write_text(json.dumps(metadata), encoding="utf-8")
    marker = f"<!-- public-quality-target: {target} -->\n"
    for name in ("README.md", "README.ja.md", "README.zh-CN.md"):
        (root / name).write_text(marker, encoding="utf-8")
    (root / "docs" / "installation.md").write_text(marker, encoding="utf-8")
    return metadata


def test_release_contract_accepts_consistent_public_quality_target(tmp_path):
    metadata = write_release_contract_fixture(tmp_path)
    assert release_contract_issues(tmp_path, metadata) == []


def test_release_contract_rejects_documentation_drift(tmp_path):
    metadata = write_release_contract_fixture(tmp_path)
    (tmp_path / "README.ja.md").write_text("<!-- public-quality-target: stale -->\n", encoding="utf-8")
    assert release_contract_issues(tmp_path, metadata) == [
        "README.ja.md: public quality target differs from release.json"
    ]


def test_release_contract_rejects_invalid_target(tmp_path):
    metadata = write_release_contract_fixture(tmp_path, target="quality; rm -rf")
    assert release_contract_issues(tmp_path, metadata) == [
        "release.json public project quality target is missing or invalid"
    ]
