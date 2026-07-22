"""Fail-closed disable/enable state transitions for an installed Cockpit."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def disable(state: dict[str, Any]) -> dict[str, Any]:
    """Set disabled state while preserving runtime, policy, evidence, and regions."""
    if state.get("state") == "purged":
        return {"state": "blocked", "reason": "purged_installation", "writes": []}
    if state.get("state") == "disabled":
        return {"state": "disabled", "idempotent": True, "writes": []}
    result = deepcopy(state)
    result["state"] = "disabled"
    result["disableEvidence"] = {
        "reason": "explicit_disable",
        "preserved": ["runtime", "policy", "evidence", "archive", "managedRegions"],
    }
    result["blockingEntry"] = True
    return {
        "state": "disabled",
        "writes": ["state", "disableEvidence", "blockingEntry"],
        "stateAfter": result,
    }


def enable(state: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    """Restore active state only when every integrity/readiness check passes."""
    if state.get("state") == "active":
        return {"state": "active", "idempotent": True, "writes": []}
    required = ("runtimeIntegrity", "manifest", "projectProfile", "policy", "adoptionReadiness")
    failed = [name for name in required if checks.get(name) is not True]
    if failed:
        return {
            "state": "disabled",
            "reason": "readiness_failed",
            "failedChecks": failed,
            "writes": [],
            "resumeCondition": "resolve failed checks and retry",
        }
    result = deepcopy(state)
    result.update({"state": "active", "blockingEntry": False})
    return {"state": "active", "writes": ["state", "blockingEntry"], "stateAfter": result}
