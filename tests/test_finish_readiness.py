import ai_finish


def summary(*, verification="passed", unknowns=None, residual_risks=None):
    return {
        "verification": [
            {"check": "quality", "result": verification},
        ],
        "unknownsRemaining": [] if unknowns is None else unknowns,
        "residualRisks": [] if residual_risks is None else residual_risks,
        "reviewReadiness": {
            "status": "not_ready",
            "reason": "Initial skeleton.",
            "expectedReviewFocus": ["review"],
        },
    }


def test_promote_review_readiness_marks_fully_verified_summary_ready():
    result = ai_finish.promote_review_readiness(summary())

    assert result["status"] == "ready"
    assert "required verification" in result["reason"]
    assert result["expectedReviewFocus"] == ["review"]


def test_promote_review_readiness_preserves_residual_risk_signal():
    result = ai_finish.promote_review_readiness(
        summary(residual_risks=[{"level": "medium", "area": "review", "detail": "focus"}])
    )

    assert result["status"] == "ready_with_risks"
    assert "residual risk" in result["reason"]


def test_promote_review_readiness_remains_not_ready_for_incomplete_evidence():
    failed = ai_finish.promote_review_readiness(summary(verification="failed"))
    unknown = ai_finish.promote_review_readiness(summary(unknowns=["external review"]))

    assert failed["status"] == "not_ready"
    assert unknown["status"] == "not_ready"


def test_promote_review_readiness_requires_acceptance_evidence_for_v2():
    result = ai_finish.promote_review_readiness(
        summary(),
        {
            "contractVersion": 2,
            "acceptance": ["A1: behavior is mapped"],
            "riskAssessment": {"level": "low"},
        },
    )

    assert result["status"] == "not_ready"
    assert "Acceptance evidence" in result["reason"]


def test_finish_archive_message_is_not_lifecycle_closure():
    output = ai_finish.archive_next_steps("example")

    assert "lifecycle is not closed" in output
    assert "make ai-close-work-item TASK=example" in output


def test_promote_review_readiness_does_not_override_failed_stabilization_evidence():
    result = ai_finish.promote_review_readiness(
        summary(verification="failed"),
        {"contractVersion": 2, "acceptance": []},
    )

    assert result["status"] == "not_ready"
