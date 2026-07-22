from scripts.ai_purge import purge


def _facts():
    return {
        "candidates": ["runtime.py", "business.py", "audit.json"],
        "protected": ["business.py", "audit.json"],
        "exportVerified": True,
    }


def test_unconfirmed_purge_blocks_and_shows_list():
    result = purge(_facts())
    assert result["state"] == "needs_human_confirmation" and result["deletionList"] == [
        "runtime.py"
    ]


def test_export_failure_blocks():
    result = purge({**_facts(), "exportVerified": False}, True, True)
    assert result["state"] == "blocked" and result["writes"] == []


def test_protected_paths_are_excluded():
    assert (
        "business.py" not in purge(_facts())["deletionList"]
        and "audit.json" not in purge(_facts())["deletionList"]
    )


def test_double_confirmation_returns_purged_receipt():
    result = purge(_facts(), True, True)
    assert (
        result["state"] == "purged"
        and result["receipt"]["evidenceDigest"] == result["evidenceDigest"]
    )
