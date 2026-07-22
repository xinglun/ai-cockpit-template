from scripts.ai_rollback import build_snapshot, execute_rollback, plan_rollback


def _snapshot(migration=None):
    return build_snapshot(
        "up-1",
        {"manifestHash": "before"},
        {"version": "1"},
        {"ci": ["gate"]},
        {"runtime.py": "old"},
        {"project": "changed"},
        migration or {"rollback": "invertible"},
        ["verify smoke"],
    )


def test_complete_rollback_restores_owned_content_and_preserves_project_config():
    snap = _snapshot()
    proposal = plan_rollback(snap, {"manifestHash": "before"}, {"project": "changed"})
    result = execute_rollback(
        snap,
        proposal,
        {"manifestHash": "before", "runtime": {"runtime.py": "new"}},
        {"project": "changed"},
        confirm=True,
    )
    assert (
        result["state"] == "rolled_back"
        and result["stateAfter"]["runtime"]["runtime.py"] == "old"
        and result["projectConfig"] == {"project": "changed"}
    )


def test_unconfirmed_rollback_has_zero_writes():
    snap = _snapshot()
    proposal = plan_rollback(snap, {"manifestHash": "before"}, {})
    assert (
        execute_rollback(snap, proposal, {"manifestHash": "before"}, {}, confirm=False)["writes"]
        == []
    )


def test_drift_blocks_without_writes():
    snap = _snapshot()
    proposal = plan_rollback(snap, {"manifestHash": "after"}, {})
    assert (
        proposal["state"] == "blocked"
        and execute_rollback(snap, proposal, {"manifestHash": "after"}, {})["writes"] == []
    )


def test_missing_snapshot_blocks():
    assert plan_rollback(None, {}, {})["reason"] == "snapshot_missing"


def test_project_owned_drift_is_marked_preserved():
    assert (
        plan_rollback(_snapshot(), {"manifestHash": "before"}, {"project": "new"})[
            "projectConfigPreserved"
        ]
        is True
    )


def test_non_invertible_migration_returns_partial_rollback():
    snap = _snapshot({"rollback": "partial_rollback"})
    proposal = plan_rollback(snap, {"manifestHash": "before"}, {})
    assert (
        proposal["state"] == "partial_rollback"
        and execute_rollback(snap, proposal, {"manifestHash": "before"}, {})["writes"] == []
    )
