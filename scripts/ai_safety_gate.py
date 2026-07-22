"""Return structured fail-closed safety decisions for lifecycle boundaries."""

from __future__ import annotations

from typing import Any


def evaluate(case: str, evidence: dict[str, Any]) -> dict[str, Any]:
    dangerous = {"silent_overwrite", "silent_delete", "drift", "unconfirmed", "forged_execution"}
    if case in dangerous or not evidence.get("verified", False):
        return {
            "state": "blocked",
            "reason": case if case in dangerous else "evidence_not_verified",
            "evidence": evidence,
            "resumeCondition": "provide verified evidence and explicit confirmation",
            "policyReference": "lifecycle-safety-gate",
        }
    return {
        "state": "allowed",
        "reason": case,
        "evidence": evidence,
        "resumeCondition": None,
        "policyReference": "lifecycle-safety-gate",
    }
