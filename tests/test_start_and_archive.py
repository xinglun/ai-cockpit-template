import json
import sys
from pathlib import Path

import ai_archive_work_item
import ai_start


def test_ai_start_default_contains_agent_risk_gate(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(ai_start, "capture_dirty_baseline", lambda: [])
    monkeypatch.setattr(ai_start, "create_observability", lambda **_: type("Obs", (), {"work_item_started": lambda *a, **k: None})())
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "sample", "--mode", "code"])

    assert ai_start.main() == 0
    contract = json.loads((active / "sample.contract.json").read_text(encoding="utf-8"))
    checks = [item["check"] for item in contract["verification"]]
    assert "aiAgentRisk" in checks
    assert "aiCheckpoint" in checks
    assert "aiReviewPolicy" in checks
    assert contract["contractVersion"] == 2
    assert contract["notCodable"] is False
    assert contract["baseCommit"] == "a" * 40
    assert contract["checkpointPolicy"]["requiredStages"] == ["before_edit", "before_finish"]


def test_ai_start_requires_initial_commit(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "")
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "sample"])

    assert ai_start.main() == 1
    assert not (active / "sample.contract.json").exists()


def test_archive_refuses_to_overwrite_existing_audit_record(tmp_path, monkeypatch):
    active = tmp_path / "active"
    archive = tmp_path / "archive"
    active.mkdir()
    contract = active / "task.contract.json"
    contract.write_text(json.dumps({"workItemId": "task", "mode": "review"}), encoding="utf-8")
    year_dir = archive / str(__import__("datetime").datetime.now().year)
    year_dir.mkdir(parents=True)
    (year_dir / contract.name).write_text("existing", encoding="utf-8")
    monkeypatch.setattr(ai_archive_work_item, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive)
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["ai_archive_work_item.py", str(contract)])

    assert ai_archive_work_item.main() == 1


def test_ai_start_journeys(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(ai_start, "capture_dirty_baseline", lambda: [])
    monkeypatch.setattr(ai_start, "create_observability", lambda **_: type("Obs", (), {"work_item_started": lambda *a, **k: None})())

    # Test refactor journey
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "refactor_task", "--mode", "code", "--journey", "refactor"])
    assert ai_start.main() == 0
    contract = json.loads((active / "refactor_task.contract.json").read_text(encoding="utf-8"))
    summary = json.loads((active / "refactor_task.summary.json").read_text(encoding="utf-8"))
    assert "Zero functional changes allowed." in contract["guidelines"]
    assert "Adding new features" in contract["outOfScope"]
    assert contract["destructiveChangePolicy"]["allowed"] is False
    assert any(item["guideline"] == "Zero functional changes allowed." for item in summary["guidelinesCompliance"])

    # Test cleanup journey
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "cleanup_task", "--mode", "code", "--journey", "cleanup"])
    assert ai_start.main() == 0
    contract_c = json.loads((active / "cleanup_task.contract.json").read_text(encoding="utf-8"))
    assert contract_c["destructiveChangePolicy"]["allowed"] is True
    assert contract_c["destructiveChangePolicy"]["requiresHumanApproval"] is True
