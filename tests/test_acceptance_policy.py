from ai_acceptance_policy import acceptance_signal


def test_acceptance_policy_covers_missing_verification_and_ready():
    contract = {"acceptance": ["done"]}
    assert acceptance_signal(contract, None, {})["value"] == "unknown"
    assert (
        acceptance_signal(
            contract, {"reviewReadiness": {"status": "ready"}}, {"value": "incomplete"}
        )["value"]
        == "incomplete"
    )
    assert (
        acceptance_signal(contract, {"reviewReadiness": {"status": "ready"}}, {"value": "passed"})[
            "value"
        ]
        == "complete"
    )
