"""Build a confirmation-gated, preserve-evidence uninstall proposal."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

MODES = ("disable", "preserve-evidence", "purge")


def build_proposal(
    facts: dict[str, Any], mode: str = "preserve-evidence", confirmed: bool = False
) -> dict[str, Any]:
    """Return Phase A evidence without mutating repository state."""
    if mode not in MODES:
        return {"state": "blocked", "reason": "invalid_mode", "writes": []}
    if facts.get("drift") or facts.get("unknownOwnership"):
        return {
            "state": "blocked",
            "reason": "drift_or_unknown_ownership",
            "writes": [],
            "resumeCondition": "reconcile facts and ownership",
        }
    evidence = [
        "bootstrap",
        "archive",
        "human_decisions",
        "project_policy",
        "complexity_baseline",
        "audit",
    ]
    deletion = [
        item for item in facts.get("runtimeFiles", []) if item not in facts.get("projectOwned", [])
    ]
    proposal = {
        "state": "confirmed" if confirmed else "needs_human_confirmation",
        "mode": mode,
        "phase": "A",
        "writes": [],
        "deletionList": deletion,
        "preserveEvidence": evidence,
        "evidenceExport": {
            "required": True,
            "bundle": f".ai/upgrade/uninstall-evidence/{facts.get('sessionId', 'pending')}.json",
        },
        "detachedUninstaller": {"required": True, "sessionId": facts.get("sessionId", "pending")},
        "receipt": {"required": True, "state": "pending"},
    }
    if mode == "purge" and not confirmed:
        proposal["state"] = "needs_human_confirmation"
        proposal["warning"] = "purge is destructive and evidence export must complete first"
    return deepcopy(proposal)
