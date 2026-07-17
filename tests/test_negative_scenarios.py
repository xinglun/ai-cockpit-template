import ai_critical_domain_guards as guards


def c(text):
    return {"intent": {"problem": text, "rationale": text, "constraints": []}}


def test_ten_negative_scenario_families_fail_closed():
    cases = [
        (guards.critical_domain_signal, "authentication change"),
        (guards.critical_domain_signal, "authorization change"),
        (guards.critical_domain_signal, "payment change"),
        (guards.critical_domain_signal, "personal data change"),
        (guards.critical_domain_signal, "secret rotation"),
        (guards.critical_domain_signal, "production release"),
        (guards.governance_bypass_signal, "bypass approval"),
        (guards.evidence_forgery_signal, "fake evidence"),
        (guards.production_operation_signal, "run in production"),
        (guards.governance_bypass_signal, "skip review"),
    ]
    for check, text in cases:
        assert check(c(text))["value"] == "Inconsistent"


def test_safe_local_alternative_is_present_for_critical_operation():
    result = guards.production_operation_signal(c("run in production"))
    assert "safe alternative" in " ".join(result["evidence"])
