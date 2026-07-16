import json
import sys

import ai_check_agent_risk


def test_agent_risk_helpers_extract_required_commands_and_statuses():
    contract = {"verification": [{"check": "quality", "required": True}, "bad"]}
    summary = {"verification": [{"check": "quality", "result": "passed"}]}

    assert ai_check_agent_risk.command_prefixes(contract) == ["quality"]
    assert ai_check_agent_risk.has_required_gate(["quality"], "quality")
    assert ai_check_agent_risk.matching_required_commands(["quality", "quality"], "quality") == [
        "quality",
        "quality",
    ]
    assert ai_check_agent_risk.summary_status(summary) == {"quality": "passed"}
    assert ai_check_agent_risk.checkpoint_evidence({"checkpointEvidence": [{"stage": "x"}]})


def test_agent_risk_rejects_unknowns_in_code_mode():
    issues = ai_check_agent_risk.validate_agent_risks(
        {
            "mode": "code",
            "unknowns": ["open"],
            "notCodable": False,
            "executionDecision": {"status": "continue"},
            "agentCapability": {"canImplement": True},
            "verification": [],
        },
        None,
    )
    assert any("mode code cannot proceed" in issue for issue in issues)


def test_agent_risk_rejects_human_decision_conflict():
    issues = ai_check_agent_risk.validate_agent_risks(
        {
            "mode": "code",
            "unknowns": [],
            "notCodable": False,
            "executionDecision": {"status": "continue"},
            "agentCapability": {"needsHumanDecision": True},
            "verification": [],
        },
        None,
    )
    assert any("needsHumanDecision" in issue for issue in issues)


def test_agent_risk_accepts_complete_gates_and_checkpoints():
    gates = ["aiWorkItem", "aiScope", "aiAgentRisk", "aiSummary", "aiStatus", "aiStatusCheck"]
    contract = {
        "mode": "code",
        "unknowns": [],
        "notCodable": False,
        "executionDecision": {"status": "continue"},
        "agentCapability": {"canImplement": True, "needsHumanDecision": False},
        "verification": [{"check": gate, "required": True} for gate in gates],
        "acceptance": ["done"],
        "checkpointPolicy": {
            "requiredBeforeFinish": True,
            "requiredStages": ["before_edit", "before_finish"],
        },
    }
    summary = {
        "verification": [{"check": gate, "result": "passed"} for gate in gates],
        "checkpointEvidence": [
            {
                "stage": stage,
                "recorded": True,
                "contractHash": "hash",
                "acceptanceCount": 1,
                "unknownCount": 0,
                "requiredChecks": len(gates),
                "requiredChecksPassed": len(gates),
            }
            for stage in ("before_edit", "before_finish")
        ],
    }
    assert (
        ai_check_agent_risk.validate_agent_risks(contract, summary, expected_contract_hash="hash")
        == []
    )


def test_agent_risk_accepts_checkpoint_full_hash_when_expected_hash_is_short():
    contract = {
        "verification": [
            {"check": gate, "required": True}
            for gate in (
                "aiWorkItem",
                "aiScope",
                "aiAgentRisk",
                "aiSummary",
                "aiStatus",
                "aiStatusCheck",
            )
        ],
        "acceptance": ["done"],
        "unknowns": [],
        "checkpointPolicy": {"requiredBeforeFinish": True, "requiredStages": ["before_finish"]},
    }
    summary = {
        "verification": [
            {"check": gate, "result": "passed"}
            for gate in (
                "aiWorkItem",
                "aiScope",
                "aiAgentRisk",
                "aiSummary",
                "aiStatus",
                "aiStatusCheck",
            )
        ],
        "checkpointEvidence": [
            {
                "stage": "before_finish",
                "recorded": True,
                "contractHash": "0123456789abcdef0123456789abcdef",
                "acceptanceCount": 1,
                "unknownCount": 0,
                "requiredChecks": 6,
                "requiredChecksPassed": 6,
            }
        ],
    }
    assert (
        ai_check_agent_risk.validate_agent_risks(
            contract, summary, expected_contract_hash="0123456789abcdef"
        )
        == []
    )


def test_agent_risk_rejects_missing_gate_and_failed_required_gate():
    contract = {
        "verification": [
            {"check": "quality", "required": True},
            {"check": "aiWorkItem", "required": True},
            {"check": "aiAgentRisk", "required": True},
        ],
        "mode": "code",
        "unknowns": [],
        "notCodable": False,
        "executionDecision": {"status": "continue"},
        "agentCapability": {"needsHumanDecision": False},
    }
    issues = ai_check_agent_risk.validate_agent_risks(
        contract,
        {
            "verification": [
                {"check": "quality", "result": "failed"},
                {"check": "aiWorkItem", "result": "failed"},
            ]
        },
    )
    assert any("missing required AI hard gate" in issue for issue in issues)
    assert any(
        "required AI hard gate is not passed in Summary: aiWorkItem" in issue for issue in issues
    )


def test_agent_risk_rejects_invalid_checkpoint_evidence():
    contract = {
        "verification": [],
        "acceptance": ["done"],
        "unknowns": [],
        "checkpointPolicy": {
            "requiredBeforeFinish": True,
            "requiredStages": ["before_finish"],
        },
    }
    summary = {
        "checkpointEvidence": [
            {
                "stage": "before_finish",
                "recorded": True,
                "contractHash": "stale",
                "acceptanceCount": 0,
                "unknownCount": 1,
                "requiredChecks": 1,
                "requiredChecksPassed": 0,
            }
        ]
    }
    issues = ai_check_agent_risk.validate_agent_risks(
        contract, summary, expected_contract_hash="expected"
    )
    assert any("contractHash is stale" in issue for issue in issues)
    assert any("acceptanceCount is stale" in issue for issue in issues)
    assert any("unknownCount is stale" in issue for issue in issues)
    assert any("requiredChecks is stale" in issue for issue in issues)


def test_agent_risk_rejects_missing_checkpoint_and_invalid_counts():
    contract = {
        "verification": [{"check": "quality", "required": True}],
        "acceptance": ["done"],
        "unknowns": ["open"],
        "notCodable": True,
        "executionDecision": {"status": "continue"},
        "agentCapability": {"canImplement": True},
        "checkpointPolicy": {
            "requiredBeforeFinish": True,
            "requiredStages": ["before_edit", "before_finish"],
        },
    }
    summary = {
        "checkpointEvidence": [
            {
                "stage": "before_finish",
                "recorded": True,
                "contractHash": "hash",
                "acceptanceCount": "one",
                "unknownCount": 1,
                "requiredChecks": 1,
                "requiredChecksPassed": 1,
            }
        ]
    }
    issues = ai_check_agent_risk.validate_agent_risks(contract, summary)
    assert any("executionDecision.status" in issue for issue in issues)
    assert any("canImplement false" in issue for issue in issues)
    assert any("missing checkpointEvidence" in issue for issue in issues)
    assert any("acceptanceCount must be integer" in issue for issue in issues)


def test_agent_risk_accepts_non_coding_blocked_contract_without_capability():
    gates = ["aiWorkItem", "aiScope", "aiAgentRisk", "aiSummary", "aiStatus", "aiStatusCheck"]
    contract = {
        "mode": "investigate",
        "unknowns": ["open"],
        "notCodable": False,
        "executionDecision": {"status": "defer"},
        "agentCapability": {},
        "verification": [{"check": gate, "required": True} for gate in gates],
    }
    summary = {"verification": [{"check": gate, "result": "passed"} for gate in gates]}
    assert ai_check_agent_risk.validate_agent_risks(contract, summary) == []


def test_agent_risk_main_handles_skip_and_success(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["ai_check_agent_risk"])
    assert ai_check_agent_risk.main() == 0

    gates = ["aiWorkItem", "aiScope", "aiAgentRisk", "aiSummary", "aiStatus", "aiStatusCheck"]
    contract_path = tmp_path / "contract.json"
    summary_path = tmp_path / "summary.json"
    contract_path.write_text(
        json.dumps(
            {
                "workItemId": "coverage",
                "verification": [{"check": gate, "required": True} for gate in gates],
            }
        ),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps({"verification": [{"check": gate, "result": "passed"} for gate in gates]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_check_agent_risk", "--contract", str(contract_path), "--summary", str(summary_path)],
    )
    assert ai_check_agent_risk.main() == 0
