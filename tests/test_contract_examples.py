import copy
import json
from pathlib import Path

import ai_check_agent_risk
import ai_start


ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    return json.loads((ROOT / ".ai" / "work-items" / "_templates" / name).read_text(encoding="utf-8"))


def test_static_examples_match_ai_start_defaults():
    contract = load("work_item_contract.example.json")
    summary = load("work_item_summary.example.json")

    assert contract["verification"] == ai_start.default_verification()
    assert contract["checkpointPolicy"]["requiredStages"] == ai_start.DEFAULT_CHECKPOINT_STAGES
    assert [item["check"] for item in summary["verification"]] == ai_start.DEFAULT_VERIFICATION_CHECKS
    assert [item["stage"] for item in summary["checkpointEvidence"]] == ai_start.DEFAULT_CHECKPOINT_STAGES


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
