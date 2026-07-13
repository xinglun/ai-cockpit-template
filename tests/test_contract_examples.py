import copy
import json
from pathlib import Path

import ai_check_agent_risk
import ai_start


ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    return json.loads(
        (ROOT / ".ai" / "work-items" / "_templates" / name).read_text(encoding="utf-8")
    )


def test_static_examples_match_ai_start_defaults():
    contract = load("work_item_contract.example.json")
    summary = load("work_item_summary.example.json")

    assert contract["verification"] == ai_start.default_verification()
    assert [item["scenario"] for item in contract["scenarioCoverage"]] == [
        "example verified scenario",
        "example unverified scenario",
        "example not applicable scenario",
    ]
    assert contract["checkpointPolicy"]["requiredStages"] == ai_start.DEFAULT_CHECKPOINT_STAGES
    assert [
        item["check"] for item in summary["verification"]
    ] == ai_start.DEFAULT_VERIFICATION_CHECKS
    assert [item["scenario"] for item in summary["scenarioCoverage"]] == [
        "example verified scenario",
        "example unverified scenario",
        "example not applicable scenario",
    ]
    assert summary["summaryVersion"] == 2
    assert summary["followUps"] == [
        "Verify the unverified scenario after the external system run completes."
    ]
    assert summary["unverifiedScenarios"] == ["example unverified scenario"]
    assert [
        item["stage"] for item in summary["checkpointEvidence"]
    ] == ai_start.DEFAULT_CHECKPOINT_STAGES
    assert summary["intentAlignment"] == {}


def test_example_contract_contains_all_agent_risk_hard_gates():
    contract = load("work_item_contract.example.json")
    summary = load("work_item_summary.example.json")
    simulated = copy.deepcopy(summary)
    for item in simulated["verification"]:
        if item["check"] != "aiAgentRisk":
            item["result"] = "passed"

    assert ai_check_agent_risk.validate_agent_risks(contract, simulated) == []


def test_example_contract_includes_problem_statement():
    contract = load("work_item_contract.example.json")

    assert contract["problemStatement"]
    assert "task solves" in contract["problemStatement"]


def test_language_example_readmes_include_default_verification_checks():
    readmes = sorted((ROOT / "examples").glob("*/README.md"))
    required = [f'"check": "{check}"' for check in ai_start.DEFAULT_VERIFICATION_CHECKS]

    assert len(readmes) == 11
    for path in readmes:
        text = path.read_text(encoding="utf-8")
        for check in required:
            assert check in text, f"{path.relative_to(ROOT)} is missing {check}"
