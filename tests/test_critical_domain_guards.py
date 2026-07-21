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


def operation(target, action="test", environment="sandbox", effect="mock"):
    value = contract("structured critical-domain operation")
    value["requestedOperation"] = {
        "target": target,
        "action": action,
        "environment": environment,
        "effect": effect,
        "authorityRequired": False,
    }
    return value


def test_safe_payment_sandbox_and_documentation_are_ready():
    assert (
        ai_critical_domain_guards.critical_domain_signal(operation("payment", effect="mock"))[
            "value"
        ]
        == "Ready"
    )
    assert (
        ai_critical_domain_guards.critical_domain_signal(
            operation("payment", action="document", effect="describe")
        )["value"]
        == "Ready"
    )


def test_dangerous_payment_effect_is_blocked_with_structured_evidence():
    result = ai_critical_domain_guards.critical_domain_signal(
        operation("payment", action="modify", environment="production", effect="force_success")
    )
    assert result["value"] == "Inconsistent"
    evidence = " ".join(result["evidence"])
    assert "signalId" in evidence and "policy" in evidence and "resume" in evidence


def test_safe_authentication_test_is_ready():
    assert (
        ai_critical_domain_guards.critical_domain_signal(
            operation("authentication", effect="mock")
        )["value"]
        == "Ready"
    )
