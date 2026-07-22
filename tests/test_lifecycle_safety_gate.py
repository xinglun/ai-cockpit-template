from scripts.ai_safety_gate import evaluate


def test_dangerous_cases_fail_closed():
    for case in ("silent_overwrite", "silent_delete", "drift", "unconfirmed", "forged_execution"):
        result = evaluate(case, {"verified": True})
        assert (
            result["state"] == "blocked" and result["resumeCondition"] and result["policyReference"]
        )


def test_safe_boundaries_pass():
    for case in ("no_op", "documentation", "sandbox_mock", "cancelled"):
        assert evaluate(case, {"verified": True})["state"] == "allowed"


def test_unverified_evidence_blocks_even_for_unknown_case():
    result = evaluate("execution_claim", {"verified": False})
    assert result["state"] == "blocked" and result["reason"] == "evidence_not_verified"
