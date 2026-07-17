"""Fail-closed readiness policy shared by Preflight callers."""

# mypy: ignore-errors
from __future__ import annotations
from typing import Any
from pathlib import Path


def readiness_state(root: Path) -> dict[str, Any]:
    """Derive installed, calibrated, and production-ready states separately."""
    installed = (root / ".ai" / "cockpit" / "version.json").is_file()
    profile = root / ".ai" / "project_profile.yaml"
    guards = root / ".ai" / "guards" / "coverage_policy.yaml"
    calibrated = installed and profile.is_file() and guards.is_file()
    ci = (root / ".github" / "workflows").is_dir() or (root / ".gitlab-ci.yml").is_file()
    review = (root / ".ai" / "guards" / "ai_review_policy.yaml").is_file()
    production_ready = calibrated and ci and review
    return {
        "state": "production_ready"
        if production_ready
        else (
            "calibration_complete"
            if calibrated
            else ("adoption_installed" if installed else "not_installed")
        ),
        "adoptionInstalled": installed,
        "calibrationComplete": calibrated,
        "productionReady": production_ready,
        "evidence": {
            "profile": profile.is_file(),
            "guards": guards.is_file(),
            "ci": ci,
            "reviewPolicy": review,
        },
    }


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
