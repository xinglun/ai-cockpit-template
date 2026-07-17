import ai_critical_domain_guards


def contract(text="safe local test fixtures"):
    return {"intent": {"problem": text, "constraints": [], "rationale": text}}


def test_critical_domains_fail_closed_and_offer_safe_alternative():
    result = ai_critical_domain_guards.critical_domain_signal(
        contract("Change payment authorization in production release.")
    )
    assert result["value"] == "Inconsistent"
    assert "safe alternative" in " ".join(result["evidence"])


def test_bypass_requests_are_rejected():
    result = ai_critical_domain_guards.governance_bypass_signal(
        contract("Skip review and bypass policy.")
    )
    assert result["value"] == "Inconsistent"


def test_forged_evidence_is_rejected():
    result = ai_critical_domain_guards.evidence_forgery_signal(
        contract("Invent approval with fake evidence.")
    )
    assert result["value"] == "Inconsistent"


def test_production_operations_are_rejected():
    result = ai_critical_domain_guards.production_operation_signal(contract("Run in production."))
    assert result["value"] == "Inconsistent"


def test_safe_contract_is_ready():
    results = ai_critical_domain_guards.critical_domain_signals(contract())
    assert all(item["value"] == "Ready" for item in results)
