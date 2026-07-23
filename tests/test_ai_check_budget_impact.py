import ai_check_budget_impact


def test_budget_overrun_requires_repayment_work_item():
    issues = ai_check_budget_impact.validate_budget_impact(
        {"budgetImpact": {"approved": False}},
        {"pythonLines": 101},
        {"max": {"pythonLines": 100}},
    )
    assert "pythonLines exceeds policy max" in issues[0]
    assert "repaymentWorkItem" in issues[1]


def test_budget_with_explicit_repayment_is_allowed():
    assert (
        ai_check_budget_impact.validate_budget_impact(
            {
                "budgetImpact": {
                    "approved": True,
                    "repaymentWorkItem": "budget-repair",
                    "repaymentRecords": ["record-1"],
                }
            },
            {"pythonLines": 101},
            {"max": {"pythonLines": 100}},
        )
        == []
    )


def test_declared_budget_projection_is_checked_before_implementation():
    issues = ai_check_budget_impact.validate_budget_impact(
        {
            "budgetImpact": {
                "expectedMetrics": {"pythonLines": 101},
                "approved": False,
            }
        },
        {"pythonLines": 100},
        {"max": {"pythonLines": 100}},
    )
    assert "pythonLines exceeds policy max" in issues[0]


def test_string_valued_policy_limit_is_checked_before_implementation():
    issues = ai_check_budget_impact.validate_budget_impact(
        {"budgetImpact": {"expectedMetrics": {"archiveGrowth": 493}, "approved": False}},
        {},
        {"max": {"archiveGrowth": "492"}},
    )
    assert "archiveGrowth exceeds policy max" in issues[0]


def test_bounded_future_reservation_is_checked_against_policy():
    assert (
        ai_check_budget_impact.validate_budget_impact(
            {
                "budgetImpact": {
                    "expectedMetrics": {"archiveGrowth": 496},
                    "reservedFutureMetrics": {"archiveGrowth": 497},
                    "approved": True,
                    "repaymentWorkItem": "budget-window",
                    "repaymentRecords": ["policy"],
                }
            },
            {"archiveGrowth": 495},
            {"max": {"archiveGrowth": 497}},
        )
        == []
    )
