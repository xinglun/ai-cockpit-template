from scripts.ai_disable_enable import disable, enable


def _state():
    return {
        "state": "active",
        "runtime": {"x": 1},
        "policy": {"gate": True},
        "evidence": ["receipt"],
        "archive": ["summary"],
        "managedRegions": {"ci": "keep"},
    }


def test_disable_preserves_runtime_policy_evidence_archive_and_regions():
    result = disable(_state())
    assert result["state"] == "disabled"
    assert result["stateAfter"]["runtime"] == {"x": 1}
    assert result["stateAfter"]["managedRegions"] == {"ci": "keep"}
    assert result["stateAfter"]["blockingEntry"] is True


def test_enable_fails_closed_when_check_fails():
    result = enable(disable(_state())["stateAfter"], {"runtimeIntegrity": True, "manifest": False})
    assert result["state"] == "disabled" and result["writes"] == []
    assert "manifest" in result["failedChecks"]


def test_enable_restores_active_after_all_checks():
    state = disable(_state())["stateAfter"]
    checks = {
        name: True
        for name in (
            "runtimeIntegrity",
            "manifest",
            "projectProfile",
            "policy",
            "adoptionReadiness",
        )
    }
    result = enable(state, checks)
    assert result["state"] == "active" and result["stateAfter"]["blockingEntry"] is False


def test_repeated_operations_are_idempotent():
    disabled = disable(_state())["stateAfter"]
    assert disable(disabled)["idempotent"] is True
    assert enable(_state(), {})["idempotent"] is True
