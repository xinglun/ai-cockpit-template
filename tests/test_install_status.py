import json

from ai_install_facts import write_fact_bundle
from ai_install_status import installed_status


def _install(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / ".ai/cockpit").mkdir(parents=True)
    (source / ".ai/cockpit/version.json").write_text(
        json.dumps({"distributionVersion": 1, "releaseVersion": "v1.0.0", "contractSchema": 1}),
        encoding="utf-8",
    )
    (target / ".ai/cockpit").mkdir(parents=True)
    (target / ".ai/cockpit/version.json").write_text(
        json.dumps({"distributionVersion": 1, "releaseVersion": "v1.0.0", "contractSchema": 1}),
        encoding="utf-8",
    )
    write_fact_bundle(
        source=source,
        target=target,
        distribution_version=json.loads((source / ".ai/cockpit/version.json").read_text()),
    )
    return target


def test_version_and_update_check_are_read_only(tmp_path):
    root = _install(tmp_path)
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    assert installed_status(root)["state"] == "active"
    assert installed_status(root, "v2.0.0")["state"] == "update_available"
    after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    assert before == after


def test_missing_or_invalid_release_evidence_fails_closed(tmp_path):
    root = _install(tmp_path)
    evidence = tmp_path / "evidence.json"
    evidence.write_text("{}", encoding="utf-8")
    status = installed_status(root, "v2.0.0", evidence)
    assert status["state"] == "error"
    assert status["readOnly"] is True


def test_missing_manifest_fails_closed(tmp_path):
    status = installed_status(tmp_path)
    assert status["state"] == "error"
    assert status["rollbackAvailable"] is False
