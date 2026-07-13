import ai_check_scenario_coverage


def test_required_verified_scenario_with_evidence_passes():
    contract = {"riskAssessment": {"level": "high", "riskTypes": ["security"]}}
    summary = {
        "scenarioCoverage": [
            {
                "scenario": "secret redaction",
                "required": True,
                "status": "verified",
                "evidence": ["pytest"],
            }
        ]
    }
    assert ai_check_scenario_coverage.detect(contract, summary) == []


def test_required_unverified_hard_risk_fails_without_ack():
    contract = {"riskAssessment": {"level": "high", "riskTypes": ["security"]}}
    summary = {
        "scenarioCoverage": [
            {
                "scenario": "installer boundary",
                "required": True,
                "status": "unverified",
                "evidence": ["planned"],
            }
        ]
    }
    findings = ai_check_scenario_coverage.detect(contract, summary)
    assert any(
        item.kind == "required_scenario_unverified" and item.severity == "error"
        for item in findings
    )


def test_missing_summary_is_reported():
    findings = ai_check_scenario_coverage.detect(
        {"riskAssessment": {"level": "high", "riskTypes": ["security"]}}, None
    )
    assert any(item.kind == "missing_summary" for item in findings)


def test_not_applicable_requires_reason():
    findings = ai_check_scenario_coverage.detect(
        {"riskAssessment": {"level": "high", "riskTypes": ["security"]}},
        {
            "scenarioCoverage": [
                {"scenario": "external auth", "required": True, "status": "not_applicable"}
            ]
        },
    )
    assert any(item.kind == "missing_reason" for item in findings)


def test_invalid_scenario_shape_is_reported():
    findings = ai_check_scenario_coverage.detect(
        {"riskAssessment": {"level": "high", "riskTypes": ["security"]}},
        {
            "scenarioCoverage": [
                {"scenario": "bad", "required": "yes", "status": "verified", "evidence": []}
            ]
        },
    )
    assert any(item.kind == "invalid_scenario_coverage" for item in findings)
