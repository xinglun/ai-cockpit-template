from ai_verification_policy import verification_signal


def test_verification_policy_distinguishes_failure_incomplete_and_passed():
    assert verification_signal(["a"], {"a": "failed"})["value"] == "failed"
    assert verification_signal(["a"], {})["value"] == "incomplete"
    assert verification_signal(["a"], {"a": "passed"})["value"] == "passed"
