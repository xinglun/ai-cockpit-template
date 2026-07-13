import json
from pathlib import Path

import pytest

import ai_governance_compression


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_CONTRACT = (
    ROOT / ".ai" / "work-items" / "archive" / "2026" / "realign_ai_cockpit_v2.contract.json"
)
ARCHIVE_SUMMARY = (
    ROOT / ".ai" / "work-items" / "archive" / "2026" / "realign_ai_cockpit_v2.summary.json"
)


def complete_contract() -> dict:
    return {
        "workItemId": "task",
        "mode": "code",
        "acceptance": ["done"],
        "intent": {
            "problem": "Fix the validator.",
            "constraints": ["Stay portable."],
            "nonGoals": ["No V3 work."],
            "rationale": "A conservative compression layer is enough.",
        },
        "guidelines": ["Keep portable"],
        "checkpointPolicy": {
            "requiredBeforeFinish": True,
            "requiredStages": ["before_edit", "before_finish"],
        },
        "riskAssessment": {"level": "low", "riskTypes": [], "reason": "fixture"},
        "verification": [{"check": "quality", "required": True}],
        "unknowns": [],
        "notCodable": False,
        "executionDecision": {"status": "continue"},
        "destructiveChangePolicy": {
            "allowed": False,
            "requiresHumanApproval": True,
            "allowPatterns": [],
        },
    }


def complete_summary() -> dict:
    return {
        "verification": [{"check": "quality", "result": "passed"}],
        "reviewReadiness": {"status": "ready", "reason": "fixture", "expectedReviewFocus": []},
        "unknownsRemaining": [],
        "guidelinesCompliance": [
            {"guideline": "Keep portable", "compliant": True, "evidence": "fixture"}
        ],
        "checkpointEvidence": [
            {
                "stage": "before_edit",
                "recorded": True,
                "contractHash": "a" * 16,
                "acceptanceCount": 1,
                "unknownCount": 0,
                "requiredChecks": 1,
                "requiredChecksPassed": 1,
            },
            {
                "stage": "before_finish",
                "recorded": True,
                "contractHash": "a" * 16,
                "acceptanceCount": 1,
                "unknownCount": 0,
                "requiredChecks": 1,
                "requiredChecksPassed": 1,
            },
        ],
        "risk": {"level": "low", "detail": "fixture"},
        "residualRisks": [],
        "intentAlignment": {
            "problemResolved": True,
            "constraintsRespected": True,
            "nonGoalsAvoided": True,
            "rationaleValidated": "fixture",
        },
        "destructiveChanges": [],
        "observedIssues": [],
        "generatedFiles": [],
        "changedFiles": [{"path": "src/app.py", "reason": "fixture"}],
    }


def signal_map(model: dict) -> dict[str, str]:
    return {item["name"]: item["value"] for item in model["signals"]}


def test_complete_low_risk_recommends_ready_for_review():
    model = ai_governance_compression.derive_governance_status(
        complete_contract(), complete_summary()
    )

    assert model["recommendation"] == "ready_for_review"
    assert signal_map(model) == {
        "Intent": "resolved",
        "Acceptance": "complete",
        "Unknowns": "resolved",
        "Verification": "passed",
        "Scenario Coverage": "not_required",
        "Guidelines": "satisfied",
        "Checkpoints": "complete",
        "Residual Risk": "low",
    }


def test_complete_medium_risk_recommends_ready_with_risks():
    contract = complete_contract()
    summary = complete_summary()
    summary["risk"]["level"] = "medium"
    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] == "ready_with_risks"
    assert model["signals"][-1]["value"] == "medium"


def test_failed_required_verification_blocks():
    contract = complete_contract()
    summary = complete_summary()
    summary["verification"][0]["result"] = "failed"

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] == "blocked"
    assert model["signals"][3]["value"] == "failed"


def test_missing_required_verification_needs_investigation():
    contract = complete_contract()
    summary = complete_summary()
    summary["verification"] = [{"check": "quality", "result": "not_run"}]

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] == "needs_investigation"
    assert model["signals"][3]["value"] == "incomplete"


def test_unknowns_remaining_needs_investigation():
    contract = complete_contract()
    summary = complete_summary()
    summary["unknownsRemaining"] = ["open item"]

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] == "needs_investigation"
    assert model["signals"][2]["value"] == "open"


def test_missing_summary_needs_investigation():
    contract = complete_contract()

    model = ai_governance_compression.derive_governance_status(contract, None)

    assert model["recommendation"] == "needs_investigation"
    assert model["signals"][1]["value"] == "unknown"


def test_contract_unknowns_keep_recommendation_conservative():
    contract = complete_contract()
    contract["unknowns"] = ["decide migration target"]
    summary = complete_summary()

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] == "needs_investigation"
    assert model["signals"][2]["value"] == "open"


def test_missing_intent_alignment_is_unknown_when_contract_has_intent():
    contract = complete_contract()
    summary = complete_summary()
    summary.pop("intentAlignment")

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] == "needs_investigation"
    assert model["signals"][0]["value"] == "unknown"


def test_no_contract_intent_is_not_applicable():
    contract = complete_contract()
    contract.pop("intent")
    summary = complete_summary()
    summary.pop("intentAlignment")

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["signals"][0]["value"] == "not_applicable"


@pytest.mark.parametrize("status", ["defer", "needs_human_decision"])
def test_deferred_execution_decisions_remain_conservative(status):
    contract = complete_contract()
    contract["executionDecision"] = {"status": status}

    model = ai_governance_compression.derive_governance_status(contract, complete_summary())

    assert model["recommendation"] == "needs_investigation"
    assert f"executionDecision is {status}" in model["decisionDrivers"]


def test_guideline_violation_blocks():
    contract = complete_contract()
    summary = complete_summary()
    summary["guidelinesCompliance"][0]["compliant"] = False

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] == "blocked"
    assert model["signals"][5]["value"] == "violated"


def test_missing_checkpoint_evidence_needs_investigation():
    contract = complete_contract()
    summary = complete_summary()
    summary["checkpointEvidence"] = [summary["checkpointEvidence"][0]]

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] == "needs_investigation"
    assert model["signals"][6]["value"] == "incomplete"


def test_scenario_coverage_unverified_can_be_ready_with_risks_when_explicitly_acknowledged():
    contract = complete_contract()
    contract["riskAssessment"] = {"level": "high", "riskTypes": ["ci"], "reason": "fixture"}
    summary = complete_summary()
    summary["reviewReadiness"]["status"] = "ready_with_risks"
    summary["residualRisks"] = [
        {
            "level": "medium",
            "area": "ci",
            "detail": "fixture",
            "reviewRecommended": True,
            "followUpCandidate": False,
        }
    ]
    summary["followUps"] = ["Verify checkout extraheader reuse in CI."]
    summary["unverifiedScenarios"] = ["GitHub Actions checkout extraheader reuse"]
    summary["scenarioCoverage"] = [
        {
            "scenario": "GitHub Actions checkout extraheader reuse",
            "required": True,
            "status": "unverified",
            "evidence": [],
            "reason": "Awaiting workflow completion.",
        }
    ]

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] == "ready_with_risks"
    assert model["signals"][4]["value"] == "incomplete"
    assert any("required scenario unverified" in item for item in model["decisionDrivers"])


def test_legacy_archive_summary_remains_readable():
    contract = json.loads(ARCHIVE_CONTRACT.read_text(encoding="utf-8"))
    summary = json.loads(ARCHIVE_SUMMARY.read_text(encoding="utf-8"))

    model = ai_governance_compression.derive_governance_status(contract, summary)

    assert model["recommendation"] in {
        "ready_for_review",
        "ready_with_risks",
        "needs_investigation",
        "blocked",
    }
    assert signal_map(model)["Intent"] in {"resolved", "unknown", "unresolved"}
