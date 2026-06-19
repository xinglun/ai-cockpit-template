import pytest

import ai_check_summary
import ai_check_work_item
import ai_common
import ai_finish


def test_plain_passed_string_is_not_execution_evidence():
    summary = {
        "workItemId": "task",
        "contractPath": "contract.json",
        "changedFiles": [{"path": "file", "reason": "changed"}],
        "verification": [{"command": "python3 -m pytest", "result": "passed"}],
        "risk": {"level": "low", "detail": "none"},
    }
    issues = ai_check_summary.validate_summary(summary, None)
    assert any("requires runner ai_finish" in issue for issue in issues)
    assert any("outputDigest" in issue for issue in issues)


def test_finish_evidence_is_complete():
    item = ai_finish.evidence(
        "projectTest", "make project-test", 0, 12, "1 passed\n",
        contract_hash="b" * 64, commit_sha="a" * 40,
        execution_contract_path=".ai/work-items/active/x.contract.json",
        execution_summary_path=".ai/work-items/active/x.summary.json",
    )
    assert item["result"] == "passed"
    assert item["exitCode"] == 0
    assert len(item["outputDigest"]) == 64


def test_pending_finish_evidence_is_not_accepted_as_completed():
    item = ai_finish.pending_evidence(
        "aiStatusCheck", "make check-ai-status", contract_hash="b" * 64, commit_sha="a" * 40,
        execution_contract_path=".ai/work-items/active/x.contract.json",
        execution_summary_path=".ai/work-items/active/x.summary.json",
    )
    assert item["result"] == "passed"
    assert item["runner"] == "ai_finish_pending"


def test_finish_orders_self_referential_gates_after_status_generation():
    commands = [
        {"check": "aiSummary"},
        {"check": "aiAgentRisk"},
        {"check": "aiStatus"},
        {"check": "projectTest"},
    ]
    ordered = sorted(commands, key=ai_finish.verification_priority)
    assert [item["check"] for item in ordered] == [
        "projectTest", "aiStatus", "aiAgentRisk", "aiSummary",
    ]


@pytest.mark.parametrize(
    "command",
    ["sh -c 'rm -rf build'", "python3 -c 'import shutil'", "git -C /tmp clean -fdx", "make dangerous-target"],
)
def test_v2_contract_rejects_raw_commands(command):
    contract = {
        "contractVersion": 2, "workItemId": "x", "mode": "code", "title": "x",
        "baseCommit": "a" * 40, "baselineDirtyPaths": [], "scope": ["x"], "outOfScope": [],
        "sources": ["x"], "unknowns": [], "notCodable": False, "acceptance": ["x"],
        "verification": [{"command": command, "required": True}],
        "destructiveChangePolicy": {"allowed": False, "requiresHumanApproval": True, "allowPatterns": []},
        "rollbackNote": "x",
    }
    assert any("command is forbidden" in issue for issue in ai_check_work_item.validate_contract(contract))


def test_registry_rejects_non_make_executable(tmp_path):
    registry = tmp_path / "checks.yaml"
    registry.write_text("checks:\n  evil:\n    command: sh -c 'rm -rf build'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must invoke an explicit Make target"):
        ai_common.render_check_command("evil", contract_path="c", summary_path="s", registry_path=registry)


def test_execution_output_redacts_project_and_home_paths():
    value = f"generated: {ai_common.PROJECT_ROOT}/status and /Users/alice/private/file.txt"
    redacted = ai_common.redact_machine_paths(value)
    assert "<PROJECT_ROOT>/status" in redacted
    assert "/Users/alice" not in redacted


def test_summary_validator_reports_nested_governance_schema_failures():
    summary = {
        "workItemId": "wrong",
        "contractPath": "contract.json",
        "changedFiles": [{"path": "", "reason": ""}],
        "verification": [{"check": "quality", "result": "unknown"}],
        "risk": {"level": "critical", "detail": ""},
        "sourcesUsed": "not-a-list",
        "unknownsRemaining": {},
        "generatedFiles": None,
        "destructiveChanges": "none",
        "observedIssues": {},
        "guidelinesCompliance": "invalid",
        "userCorrectionsCaptured": "invalid",
        "userCorrectionSolidification": "invalid",
        "knownGaps": "invalid",
        "checkpointEvidence": ["invalid", {
            "stage": "",
            "recorded": "yes",
            "detail": 1,
            "contractHash": "",
            "acceptanceCount": "one",
        }],
        "residualRisks": ["invalid", {"level": "critical", "area": "", "detail": ""}],
        "reviewReadiness": {"status": "unknown", "reason": "", "expectedReviewFocus": [""]},
        "boundaryChecks": {"": ""},
        "overclaimPrevention": "",
        "machinePath": "/Users/alice/private.txt",
    }
    contract = {
        "contractVersion": 2,
        "workItemId": "task",
        "verification": [{"check": "quality", "required": True}, {"check": "aiScope", "required": True}],
    }

    issues = ai_check_summary.validate_summary(summary, contract)
    assert len(issues) >= 25
    assert any("checkpointEvidence[0]" in issue for issue in issues)
    assert any("residualRisks[1].level" in issue for issue in issues)
    assert any("machine-specific path" in issue for issue in issues)
    assert any("missing required verification: aiScope" in issue for issue in issues)
