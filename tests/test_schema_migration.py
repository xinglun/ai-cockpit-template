from __future__ import annotations

from ai_schema_migration import MigrationError, apply_plan, build_plan


REGISTRY = {
    "versions": {"1": {}, "2": {}},
    "transitions": {
        "1->2": [
            {"old": "name", "new": "displayName"},
            {"old": "mode", "new": "mode", "default": "safe", "policyImpact": "strengthen"},
        ]
    },
}


def test_auto_migration_and_default_requires_confirmation_for_policy_change() -> None:
    plan = build_plan({"name": "Cockpit"}, from_version=1, to_version=2, registry=REGISTRY)
    assert plan["state"] == "needs_human_confirmation"
    assert apply_plan({"name": "Cockpit"}, plan)["written"] is False
    applied = apply_plan({"name": "Cockpit"}, plan, confirm=True)
    assert applied["written"] is True
    assert applied["config"]["displayName"] == "Cockpit"
    assert applied["config"]["mode"] == "safe"


def test_missing_field_without_default_blocks() -> None:
    plan = build_plan({"mode": "safe"}, from_version=1, to_version=2, registry=REGISTRY)
    result = apply_plan({"mode": "safe"}, plan, confirm=True)
    assert result["state"] == "blocked"
    assert result["written"] is False


def test_reverse_migration_is_partial_rollback() -> None:
    plan = build_plan({"displayName": "Cockpit"}, from_version=2, to_version=1, registry=REGISTRY)
    result = apply_plan({"displayName": "Cockpit"}, plan, confirm=True)
    assert result["state"] == "partial_rollback"
    assert result["written"] is False


def test_invalid_schema_fails_closed() -> None:
    try:
        build_plan({}, from_version=1, to_version=3, registry=REGISTRY)
    except MigrationError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unsupported schema must fail")
