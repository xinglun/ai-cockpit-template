from scripts.ai_uninstall_proposal import build_proposal


def _facts():
    return {
        "sessionId": "s-1",
        "runtimeFiles": ["runtime.py", "project.py"],
        "projectOwned": ["project.py"],
    }


def test_three_modes_are_explicit_and_unconfirmed_is_read_only():
    for mode in ("disable", "preserve-evidence", "purge"):
        proposal = build_proposal(_facts(), mode)
        assert (
            proposal["mode"] == mode
            and proposal["state"] == "needs_human_confirmation"
            and proposal["writes"] == []
        )


def test_preserve_evidence_retains_governance_and_project_files():
    proposal = build_proposal(_facts())
    assert (
        "archive" in proposal["preserveEvidence"]
        and "project_policy" in proposal["preserveEvidence"]
    )
    assert proposal["deletionList"] == ["runtime.py"]


def test_drift_or_unknown_ownership_blocks():
    assert build_proposal({**_facts(), "drift": True})["state"] == "blocked"
    assert build_proposal({**_facts(), "unknownOwnership": ["x"]})["state"] == "blocked"


def test_confirmed_purge_still_requires_export_and_receipt():
    proposal = build_proposal(_facts(), "purge", confirmed=True)
    assert (
        proposal["state"] == "confirmed"
        and proposal["evidenceExport"]["required"]
        and proposal["receipt"]["required"]
    )
