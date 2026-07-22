from scripts.ai_detached_uninstaller import prepare


def _facts():
    return {
        "detached": True,
        "files": ["runtime.py", "business.py", "receipt.json"],
        "preserve": ["business.py", "receipt.json"],
    }


def test_unconfirmed_detached_removal_has_zero_writes():
    result = prepare("s-1", _facts())
    assert result["state"] == "needs_human_confirmation" and result["writes"] == []


def test_drift_or_unknown_ownership_blocks():
    assert prepare("s-1", {**_facts(), "drift": True}, True)["state"] == "blocked"
    assert prepare("s-1", {**_facts(), "unknownOwnership": ["x"]}, True)["state"] == "blocked"


def test_confirmed_removal_preserves_business_and_evidence():
    result = prepare("s-1", _facts(), True)
    assert result["state"] == "completed" and result["receipt"]["removed"] == ["runtime.py"]
    assert result["receipt"]["preserved"] == ["business.py", "receipt.json"]


def test_non_detached_executor_blocks():
    assert prepare("s-1", {**_facts(), "detached": False}, True)["state"] == "blocked"
