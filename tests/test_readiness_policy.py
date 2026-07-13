from ai_readiness_policy import has_explicit_blocker


def test_explicit_blockers_are_fail_closed():
    assert has_explicit_blocker({"notCodable": True})
    assert has_explicit_blocker({"executionDecision": {"status": "block"}})
    assert has_explicit_blocker({"agentCapability": {"canImplement": False}})
    assert not has_explicit_blocker({})
