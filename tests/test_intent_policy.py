from ai_intent_policy import intent_alignment_signal


def test_intent_policy_handles_missing_and_resolved_alignment():
    assert intent_alignment_signal({}, {})["value"] == "not_applicable"
    contract = {"intent": {"problem": "fix"}}
    assert intent_alignment_signal(contract, {})["value"] == "unknown"
    assert (
        intent_alignment_signal(contract, {"intentAlignment": {"problemResolved": True}})["value"]
        == "resolved"
    )
