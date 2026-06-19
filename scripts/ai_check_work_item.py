#!/usr/bin/env python3
"""Validate the minimum Work Item Contract structure."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from ai_common import contains_machine_path, load_check_registry, load_json, non_empty_string
from ai_observability import create_observability, elapsed_ms


REQUIRED_FIELDS = (
    "contractVersion",
    "workItemId",
    "mode",
    "title",
    "scope",
    "outOfScope",
    "sources",
    "unknowns",
    "notCodable",
    "acceptance",
    "verification",
    "rollbackNote",
)
ALLOWED_FIELDS = set(REQUIRED_FIELDS) | {
    "agentCapability",
    "checkpointPolicy",
    "destructiveChangePolicy",
    "executionDecision",
    "preReviewWarnings",
    "riskAssessment",
    "baseCommit",
    "baselineDirtyPaths",
    "adoptionBootstrapPaths",
    "restrictedWriteApproval",
    "guidelines",
}
MODES = {"investigate", "author_todo", "code", "review", "cleanup"}
RISK_LEVELS = {"low", "medium", "high"}
EXECUTION_STATUSES = {"continue", "defer", "needs_human_decision", "block"}


def validate_string_list(data: dict[str, Any], key: str, *, allow_empty: bool) -> list[str]:
    issues: list[str] = []
    value = data.get(key)
    if not isinstance(value, list):
        return [f"{key} must be a list"]
    if not allow_empty and not value:
        issues.append(f"{key} must contain at least one item")
    for index, item in enumerate(value):
        if not non_empty_string(item):
            issues.append(f"{key}[{index}] must be a non-empty string")
    return issues


def validate_sources(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        return ["sources must contain at least one item"]
    for index, item in enumerate(sources):
        if non_empty_string(item):
            continue
        if isinstance(item, dict):
            if not non_empty_string(item.get("path")):
                issues.append(f"sources[{index}].path is required")
            if not non_empty_string(item.get("reason")):
                issues.append(f"sources[{index}].reason is required")
            continue
        issues.append(f"sources[{index}] must be a string or a path/reason object")
    return issues


def validate_verification(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    values = data.get("verification")
    if not isinstance(values, list) or not values:
        return ["verification must contain at least one item"]
    version = data.get("contractVersion")
    registry = load_check_registry()
    seen: set[str] = set()
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            issues.append(f"verification[{index}] must be an object")
            continue
        if version == 2:
            check_id = item.get("check")
            if not non_empty_string(check_id):
                issues.append(f"verification[{index}].check is required")
            elif check_id not in registry:
                issues.append(f"verification[{index}].check is not registered: {check_id}")
            elif check_id in seen:
                issues.append(f"verification[{index}].check is duplicated: {check_id}")
            else:
                seen.add(check_id)
            if "command" in item:
                issues.append(f"verification[{index}].command is forbidden in contractVersion 2")
        elif not non_empty_string(item.get("command")):
            issues.append(f"verification[{index}].command is required")
        if not isinstance(item.get("required"), bool):
            issues.append(f"verification[{index}].required must be boolean")
    return issues


def validate_optional_readiness(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    risk = data.get("riskAssessment")
    if risk is not None:
        if not isinstance(risk, dict):
            issues.append("riskAssessment must be an object")
        else:
            if risk.get("level") not in RISK_LEVELS:
                issues.append(f"riskAssessment.level must be one of {sorted(RISK_LEVELS)}")
            risk_types = risk.get("riskTypes")
            if not isinstance(risk_types, list) or any(not non_empty_string(item) for item in risk_types):
                issues.append("riskAssessment.riskTypes must be a list of non-empty strings")
            if not non_empty_string(risk.get("reason")):
                issues.append("riskAssessment.reason is required")

    capability = data.get("agentCapability")
    if capability is not None:
        if not isinstance(capability, dict):
            issues.append("agentCapability must be an object")
        else:
            for key in ("canImplement", "canVerify", "needsHumanDecision"):
                if not isinstance(capability.get(key), bool):
                    issues.append(f"agentCapability.{key} must be boolean")
            if "blockedReason" in capability and not isinstance(capability.get("blockedReason"), str):
                issues.append("agentCapability.blockedReason must be a string")

    decision = data.get("executionDecision")
    if decision is not None:
        if not isinstance(decision, dict):
            issues.append("executionDecision must be an object")
        else:
            if decision.get("status") not in EXECUTION_STATUSES:
                issues.append(f"executionDecision.status must be one of {sorted(EXECUTION_STATUSES)}")
            if not non_empty_string(decision.get("reason")):
                issues.append("executionDecision.reason is required")

    warnings = data.get("preReviewWarnings")
    if warnings is not None:
        if not isinstance(warnings, list) or any(not non_empty_string(item) for item in warnings):
            issues.append("preReviewWarnings must be a list of non-empty strings")

    checkpoint = data.get("checkpointPolicy")
    if checkpoint is not None:
        if not isinstance(checkpoint, dict):
            issues.append("checkpointPolicy must be an object")
        else:
            if "requiredBeforeFinish" in checkpoint and not isinstance(checkpoint.get("requiredBeforeFinish"), bool):
                issues.append("checkpointPolicy.requiredBeforeFinish must be boolean")
            stages = checkpoint.get("requiredStages")
            if stages is not None and (not isinstance(stages, list) or any(not non_empty_string(item) for item in stages)):
                issues.append("checkpointPolicy.requiredStages must be a list of non-empty strings")
            if "reason" in checkpoint and not non_empty_string(checkpoint.get("reason")):
                issues.append("checkpointPolicy.reason must be a non-empty string")

    return issues


def validate_baseline_and_approvals(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    base = data.get("baseCommit")
    requires_baseline = data.get("contractVersion") == 2
    if requires_baseline and (not non_empty_string(base) or len(str(base).strip()) < 7):
        issues.append("baseCommit must be a non-empty Git commit identifier")
    dirty = data.get("baselineDirtyPaths")
    if requires_baseline and not isinstance(dirty, list):
        issues.append("baselineDirtyPaths must be a list")
    elif isinstance(dirty, list):
        for index, item in enumerate(dirty):
            if not isinstance(item, dict):
                issues.append(f"baselineDirtyPaths[{index}] must be an object")
                continue
            for key in ("path", "status", "fingerprint"):
                if not non_empty_string(item.get(key)):
                    issues.append(f"baselineDirtyPaths[{index}].{key} is required")

    bootstrap = data.get("adoptionBootstrapPaths")
    if bootstrap is not None:
        if data.get("workItemId") != "adopt_ai_cockpit":
            issues.append("adoptionBootstrapPaths is only allowed for workItemId adopt_ai_cockpit")
        if not isinstance(bootstrap, list) or not bootstrap or any(not non_empty_string(item) for item in bootstrap):
            issues.append("adoptionBootstrapPaths must be a non-empty list of path patterns")

    destructive = data.get("destructiveChangePolicy")
    if not isinstance(destructive, dict):
        issues.append("destructiveChangePolicy must be an object")
    else:
        for key in ("allowed", "requiresHumanApproval"):
            if not isinstance(destructive.get(key), bool):
                issues.append(f"destructiveChangePolicy.{key} must be boolean")
        patterns = destructive.get("allowPatterns")
        if not isinstance(patterns, list) or any(not non_empty_string(item) for item in patterns):
            issues.append("destructiveChangePolicy.allowPatterns must be a list of non-empty strings")
        if patterns and destructive.get("allowed") is not True:
            issues.append("destructiveChangePolicy.allowPatterns require allowed true")
        evidence = destructive.get("approvalEvidence")
        if destructive.get("allowed") is True and destructive.get("requiresHumanApproval") is True:
            if not isinstance(evidence, dict) or evidence.get("approved") is not True:
                issues.append("destructive changes require approvalEvidence.approved true")
            elif not non_empty_string(evidence.get("approvedBy")) or not non_empty_string(evidence.get("reason")):
                issues.append("destructive approvalEvidence requires approvedBy and reason")

    approval = data.get("restrictedWriteApproval")
    if approval is not None:
        if not isinstance(approval, dict):
            issues.append("restrictedWriteApproval must be an object")
        else:
            if not isinstance(approval.get("approved"), bool):
                issues.append("restrictedWriteApproval.approved must be boolean")
            if approval.get("approved") is True and (
                not non_empty_string(approval.get("approvedBy")) or not non_empty_string(approval.get("reason"))
            ):
                issues.append("approved restrictedWriteApproval requires approvedBy and reason")
    return issues


def validate_contract(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in REQUIRED_FIELDS:
        if key not in data:
            issues.append(f"missing field: {key}")
    for key in data:
        if key not in ALLOWED_FIELDS:
            issues.append(f"unknown field: {key}")

    if data.get("contractVersion") not in {1, 2}:
        issues.append("contractVersion must be 1 or 2")
    if data.get("mode") not in MODES:
        issues.append(f"mode must be one of {sorted(MODES)}")
    for key in ("workItemId", "title", "rollbackNote"):
        if key in data and not non_empty_string(data.get(key)):
            issues.append(f"{key} must be a non-empty string")

    issues.extend(validate_string_list(data, "scope", allow_empty=False))
    issues.extend(validate_string_list(data, "outOfScope", allow_empty=True))
    issues.extend(validate_string_list(data, "unknowns", allow_empty=True))
    issues.extend(validate_string_list(data, "acceptance", allow_empty=False))
    if "guidelines" in data:
        issues.extend(validate_string_list(data, "guidelines", allow_empty=True))
    issues.extend(validate_sources(data))
    issues.extend(validate_verification(data))
    issues.extend(validate_optional_readiness(data))
    issues.extend(validate_baseline_and_approvals(data))

    if not isinstance(data.get("notCodable"), bool):
        issues.append("notCodable must be boolean")
    if data.get("mode") == "code" and data.get("notCodable"):
        issues.append("mode code cannot run with notCodable true")
    if data.get("mode") == "code" and data.get("unknowns"):
        issues.append("mode code cannot run while unknowns remain")
    if data.get("notCodable") or data.get("unknowns"):
        decision = data.get("executionDecision")
        status = decision.get("status") if isinstance(decision, dict) else ""
        if status == "continue":
            issues.append("unknowns or notCodable require executionDecision.status other than continue")
    def scan_machine_paths(value: Any, location: str) -> None:
        if isinstance(value, str) and contains_machine_path(value):
            issues.append(f"{location} contains a machine-specific path")
        elif isinstance(value, dict):
            for key, child in value.items():
                scan_machine_paths(child, f"{location}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan_machine_paths(child, f"{location}[{index}]")

    scan_machine_paths(data, "contract")
    return issues


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1]:
        print("Skipping work item check (no active contract provided)")
        return 0
    path = Path(sys.argv[1])
    start = time.time()
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Failed to read Work Item Contract: {exc}", file=sys.stderr)
        return 1

    obs = create_observability(work_item_id=data.get("workItemId", ""))
    issues = validate_contract(data)
    duration = elapsed_ms(start)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        obs.check_failed(check_id="aiWorkItem", duration_ms=duration, detail=f"{len(issues)} issue(s)")
        return 1
    print(f"work item contract check passed: {path}")
    obs.check_passed(check_id="aiWorkItem", duration_ms=duration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
