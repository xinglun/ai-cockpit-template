from ai_acceptance_policy import acceptance_signal
from ai_acceptance_policy import validate_acceptance_evidence


def test_acceptance_policy_covers_missing_verification_and_ready():
    contract = {"acceptance": ["done"]}
    assert acceptance_signal(contract, None, {})["value"] == "unknown"
    assert (
        acceptance_signal(
            contract, {"reviewReadiness": {"status": "ready"}}, {"value": "incomplete"}
        )["value"]
        == "incomplete"
    )
    assert (
        acceptance_signal(contract, {"reviewReadiness": {"status": "ready"}}, {"value": "passed"})[
            "value"
        ]
        == "complete"
    )


def v2_contract(*, risk="low"):
    return {
        "contractVersion": 2,
        "acceptance": ["A1: behavior is implemented", "A2: bug fix is regression tested"],
        "riskAssessment": {"level": risk},
    }


def valid_evidence():
    return {
        "acceptanceEvidence": [
            {
                "acceptanceId": "A1",
                "evidence": [
                    {
                        "type": "test",
                        "path": "tests/test_acceptance_policy.py",
                        "locator": "test_acceptance_policy_covers_missing_verification_and_ready",
                        "verification": "quality",
                    }
                ],
            },
            {
                "acceptanceId": "A2",
                "kind": "bug_fix",
                "failureScenario": "The old behavior accepted an unexecuted mapping.",
                "evidence": [
                    {
                        "type": "test",
                        "path": "tests/test_acceptance_policy.py",
                        "locator": "test_acceptance_policy_covers_missing_verification_and_ready",
                        "verification": "quality",
                    }
                ],
            },
        ]
    }


def test_v2_acceptance_evidence_mapping_is_complete_and_executed():
    issues = validate_acceptance_evidence(
        v2_contract(),
        valid_evidence(),
        [{"check": "quality", "result": "passed"}],
    )

    assert issues == []


def test_acceptance_evidence_rejects_missing_ids_paths_and_execution():
    contract = v2_contract()
    contract["acceptance"] = ["A1: behavior is missing an ID", "behavior is missing an ID"]
    summary = {
        "acceptanceEvidence": [
            {
                "acceptanceId": "A1",
                "evidence": [
                    {
                        "type": "test",
                        "path": "tests/does-not-exist.py",
                        "locator": "missing_test",
                        "verification": "quality",
                    }
                ],
            }
        ]
    }

    issues = validate_acceptance_evidence(
        contract, summary, [{"check": "quality", "result": "not_run"}]
    )

    assert "contract.acceptance[1] must start with a stable A<n>: identifier" in issues
    assert "acceptanceEvidence[0].evidence[0].path does not exist" in issues
    assert "acceptanceEvidence[0].evidence[0].verification quality was not passed" in issues


def test_high_risk_and_bug_fix_acceptance_require_review_and_failure_scenario():
    evidence = valid_evidence()
    del evidence["acceptanceEvidence"][1]["failureScenario"]
    evidence["acceptanceEvidence"][1]["kind"] = "bug_fix"
    issues = validate_acceptance_evidence(
        v2_contract(risk="high"),
        evidence,
        [{"check": "quality", "result": "passed"}],
    )

    assert "high-risk Acceptance evidence requires humanReview.completed true" in issues
    assert "bug-fix Acceptance evidence requires failureScenario" in issues
