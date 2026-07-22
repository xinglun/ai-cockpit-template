import json
from pathlib import Path

import pytest

from ai_install_facts import (
    InstallFactsError,
    canonical_json,
    validate_fact_bundle,
    write_fact_bundle,
)


def make_install_tree(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / ".ai" / "cockpit").mkdir(parents=True)
    (target / ".ai" / "guards").mkdir(parents=True)
    (target / ".ai" / "cockpit").mkdir(parents=True)
    (target / ".ai" / "work-items" / "archive").mkdir(parents=True)
    (target / ".ai" / "guards" / "policy.yaml").write_text("mode: blocking\n", encoding="utf-8")
    (target / ".ai" / "cockpit" / "version.json").write_text("{}\n", encoding="utf-8")
    (target / ".ai" / "work-items" / "archive" / "history.json").write_text(
        "{}\n", encoding="utf-8"
    )
    return source, target


def test_write_fact_bundle_contains_bound_manifest_and_all_ownerships(tmp_path):
    source, target = make_install_tree(tmp_path)
    facts = write_fact_bundle(
        source=source,
        target=target,
        distribution_version={
            "distributionVersion": 2,
            "releaseVersion": "0.5.32",
            "contractSchema": 2,
        },
    )

    assert set(facts) == {"manifest", "version", "managedRegions", "rollbackBaseline"}
    manifest = facts["manifest"]
    assert manifest["installationId"]
    assert facts["version"]["manifestHash"]
    assert {item["ownership"] for item in manifest["files"]} >= {
        "shared",
        "generated",
        "historical",
    }
    assert all(item["currentDigest"] == item["installedDigest"] for item in manifest["files"])
    assert all(item["projectModified"] is False for item in manifest["files"])
    assert all(item["ownershipClass"] for item in manifest["files"])
    assert validate_fact_bundle(target)["version"] == facts["version"]


def test_validation_reports_current_digest_and_project_modification(tmp_path):
    source, target = make_install_tree(tmp_path)
    write_fact_bundle(source=source, target=target, distribution_version={"distributionVersion": 2})
    changed = target / ".ai" / "guards" / "policy.yaml"
    changed.write_text("mode: project-change\n", encoding="utf-8")
    facts = validate_fact_bundle(target)
    item = next(
        item for item in facts["manifest"]["files"] if item["path"] == ".ai/guards/policy.yaml"
    )
    assert item["projectModified"] is True
    assert item["currentDigest"] != item["installedDigest"]


def test_fact_reads_are_deterministic_and_canonical(tmp_path):
    source, target = make_install_tree(tmp_path)
    write_fact_bundle(
        source=source,
        target=target,
        distribution_version={"distributionVersion": 2, "contractSchema": 2},
    )
    first = validate_fact_bundle(target)
    second = validate_fact_bundle(target)
    assert canonical_json(first) == canonical_json(second)


@pytest.mark.parametrize("mutation", ["missing", "malformed", "tampered"])
def test_invalid_fact_bundle_fails_closed(tmp_path, mutation):
    source, target = make_install_tree(tmp_path)
    write_fact_bundle(
        source=source,
        target=target,
        distribution_version={"distributionVersion": 2, "contractSchema": 2},
    )
    manifest_path = target / ".ai" / "install" / "manifest.json"
    if mutation == "missing":
        manifest_path.unlink()
    elif mutation == "malformed":
        manifest_path.write_text("not json\n", encoding="utf-8")
    else:
        entry = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry["files"][0]["installedDigest"] = "0" * 64
        manifest_path.write_bytes(canonical_json(entry))
    with pytest.raises(InstallFactsError):
        validate_fact_bundle(target)
