"""Fail-closed readiness policy shared by Preflight callers."""

# mypy: ignore-errors
from __future__ import annotations
from typing import Any


def has_explicit_blocker(contract: dict[str, Any]) -> bool:
    decision = (
        contract.get("executionDecision")
        if isinstance(contract.get("executionDecision"), dict)
        else {}
    )
    capability = (
        contract.get("agentCapability") if isinstance(contract.get("agentCapability"), dict) else {}
    )
    if contract.get("notCodable") is True or decision.get("status") in {
        "block",
        "defer",
        "needs_human_decision",
    }:
        return True
    return bool(
        capability
        and (
            capability.get("canImplement") is False
            or capability.get("canVerify") is False
            or capability.get("needsHumanDecision") is True
        )
    )
