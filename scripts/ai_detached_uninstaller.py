"""Model a self-contained, fail-closed detached Runtime removal executor."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def prepare(session_id: str, facts: dict[str, Any], confirm: bool = False) -> dict[str, Any]:
    """Create an execution result without deleting anything until confirmed."""
    if facts.get("drift") or facts.get("unknownOwnership") or not facts.get("detached", True):
        return {"state": "blocked", "writes": [], "reason": "drift_unknown_or_not_detached"}
    if not confirm:
        return {"state": "needs_human_confirmation", "writes": [], "sessionId": session_id}
    preserved = [item for item in facts.get("files", []) if item in facts.get("preserve", [])]
    removed = [item for item in facts.get("files", []) if item not in preserved]
    receipt = {
        "sessionId": session_id,
        "removed": removed,
        "preserved": preserved,
        "evidencePreserved": True,
        "runtimeRemovalVerified": True,
    }
    return {
        "state": "completed",
        "writes": ["runtime", "managedRegions", "receipt"],
        "receipt": deepcopy(receipt),
    }
