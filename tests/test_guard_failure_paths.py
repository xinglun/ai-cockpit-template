import json
import sys

import ai_check_backtrack
import ai_check_coverage_guard
import ai_check_guards
import ai_check_status_consistency
import ai_check_work_item


class Observer:
    def guard_violation(self, **_kwargs):
        return None

    def check_failed(self, **_kwargs):
        return None

    def check_passed(self, **_kwargs):
        return None


def test_backtrack_main_blocks_deleted_evidence(tmp_path, monkeypatch):
    policy = tmp_path / "backtrack.yaml"
    policy.write_text("reportOnly: false\n", encoding="utf-8")
    report = tmp_path / "backtrack.json"
    monkeypatch.setattr(ai_check_backtrack, "POLICY_PATH", policy)
    monkeypatch.setattr(ai_check_backtrack, "REPORT_PATH", report)
    monkeypatch.setattr(ai_check_backtrack, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_backtrack, "changed_name_status", lambda: [("D", "tests/test_service.py")])
    monkeypatch.setattr(ai_check_backtrack, "create_observability", lambda: Observer())
    monkeypatch.setattr(sys, "argv", ["ai_check_backtrack.py", "--verbose"])

    assert ai_check_backtrack.main() == 1
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "warning"


def test_coverage_guard_main_blocks_production_without_test(tmp_path, monkeypatch):
    policy = tmp_path / "coverage.yaml"
    policy.write_text(
        "reportOnly: false\nproduction:\n  include:\n    - src/**\ntests:\n  include:\n    - tests/**\n",
        encoding="utf-8",
    )
    report = tmp_path / "coverage.json"
    monkeypatch.setattr(ai_check_coverage_guard, "POLICY", policy)
    monkeypatch.setattr(ai_check_coverage_guard, "REPORT_PATH", report)
    monkeypatch.setattr(ai_check_coverage_guard, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_coverage_guard, "changed_paths", lambda: ["src/service.py"])
    monkeypatch.setattr(ai_check_coverage_guard, "create_observability", lambda: Observer())

    assert ai_check_coverage_guard.main() == 1
    assert json.loads(report.read_text(encoding="utf-8"))["items"][0]["path"] == "src/service.py"


def test_guard_main_blocks_forbidden_boundary(tmp_path, monkeypatch):
    ownership = tmp_path / "ownership.yaml"
    boundary = tmp_path / "boundary.yaml"
    ownership.write_text("target/**:\n  aiWrite: forbidden\n  reason: generated\n", encoding="utf-8")
    boundary.write_text("target/**:\n  boundary: generated_local\n  reason: generated\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_guards, "OWNERSHIP", ownership)
    monkeypatch.setattr(ai_check_guards, "BOUNDARY", boundary)
    monkeypatch.setattr(ai_check_guards, "REPORT", tmp_path / "guard.json")
    monkeypatch.setattr(ai_check_guards, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_guards, "changed_paths", lambda _contract: ["target/output.bin"])
    monkeypatch.setattr(ai_check_guards, "create_observability", lambda: Observer())
    monkeypatch.setattr(sys, "argv", ["ai_check_guards.py"])

    assert ai_check_guards.main() == 1
    assert json.loads(ai_check_guards.REPORT.read_text(encoding="utf-8"))["status"] == "error"


def test_status_consistency_main_fails_for_missing_status(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_check_status_consistency, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_status_consistency, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_check_status_consistency, "DEFAULT_STATUS", tmp_path / "missing.md")
    monkeypatch.setattr(sys, "argv", ["ai_check_status_consistency.py", "--status", str(tmp_path / "missing.md")])

    assert ai_check_status_consistency.main() == 1


def test_contract_validator_reports_multiple_invalid_governance_fields():
    contract = {
        "contractVersion": 2,
        "workItemId": "bad id",
        "mode": "code",
        "title": "",
        "baseCommit": "x",
        "baselineDirtyPaths": "dirty",
        "scope": [],
        "outOfScope": "none",
        "sources": [],
        "unknowns": ["unresolved"],
        "notCodable": True,
        "riskAssessment": {"level": "critical", "riskTypes": "bad", "reason": ""},
        "agentCapability": {"canImplement": True, "canVerify": "yes", "needsHumanDecision": False},
        "executionDecision": {"status": "continue", "reason": ""},
        "preReviewWarnings": "warning",
        "checkpointPolicy": {"requiredBeforeFinish": "yes", "requiredStages": [""]},
        "acceptance": [],
        "guidelines": [],
        "verification": [{"command": "rm -rf .", "required": True}],
        "destructiveChangePolicy": {"allowed": True, "requiresHumanApproval": True, "allowPatterns": "all"},
        "restrictedWriteApproval": {"approved": True, "approvedBy": "", "reason": ""},
        "rollbackNote": "",
    }
    issues = ai_check_work_item.validate_contract(contract)
    assert len(issues) >= 15
    assert any("mode code cannot" in issue for issue in issues)
    assert any("command is forbidden" in issue for issue in issues)
