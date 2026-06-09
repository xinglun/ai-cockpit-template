#!/usr/bin/env python3
"""Validate an AI Change Summary against a Work Item Contract."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from ai_common import PROJECT_ROOT, changed_paths, included, load_json, non_empty_string, simple_yaml_lists
from ai_observability import create_observability, elapsed_ms


SCOPE_POLICY = PROJECT_ROOT / ".ai" / "guards" / "scope_policy.yaml"
REQUIRED_FIELDS = (
    "workItemId",
    "contractPath",
    "changedFiles",
    "sourcesUsed",
    "verification",
    "unknownsRemaining",
    "risk",
    "generatedFiles",
    "destructiveChanges",
    "observedIssues",
)
RESULTS = {"passed", "failed", "not_run"}
RISK_LEVELS = {"low", "medium", "high"}
REVIEW_READINESS_STATUSES = {"not_ready", "ready", "ready_with_risks", "blocked"}


def changed_file_paths(summary: dict[str, Any]) -> set[str]:
    changed = summary.get("changedFiles")
    if not isinstance(changed, list):
        return set()
    return {
        item.get("path")
        for item in changed
        if isinstance(item, dict) and non_empty_string(item.get("path"))
    }


def summary_exempt_patterns() -> list[str]:
    policy_lists = simple_yaml_lists(SCOPE_POLICY)
    return policy_lists.get("allowAlways", [])


def validate_summary(summary: dict[str, Any], contract: dict[str, Any] | None) -> list[str]:
    issues: list[str] = []
    for key in REQUIRED_FIELDS:
        if key not in summary:
            issues.append(f"missing field: {key}")

    if contract is not None and summary.get("workItemId") != contract.get("workItemId"):
        issues.append("workItemId does not match the Contract")

    changed = summary.get("changedFiles")
    if not isinstance(changed, list) or not changed:
        issues.append("changedFiles must contain at least one item")
    elif any(not isinstance(item, dict) or not non_empty_string(item.get("path")) or not non_empty_string(item.get("reason")) for item in changed):
        issues.append("changedFiles must be a list of objects with path and reason")

    verification = summary.get("verification")
    if not isinstance(verification, list) or not verification:
        issues.append("verification must contain at least one item")
    else:
        for index, item in enumerate(verification):
            if not isinstance(item, dict):
                issues.append(f"verification[{index}] must be an object")
                continue
            if not non_empty_string(item.get("command")):
                issues.append(f"verification[{index}].command is required")
            if item.get("result") not in RESULTS:
                issues.append(f"verification[{index}].result must be one of {sorted(RESULTS)}")

    risk = summary.get("risk")
    if not isinstance(risk, dict):
        issues.append("risk must be an object")
    else:
        if risk.get("level") not in RISK_LEVELS:
            issues.append(f"risk.level must be one of {sorted(RISK_LEVELS)}")
        if not non_empty_string(risk.get("detail")):
            issues.append("risk.detail is required")

    for key in ("sourcesUsed", "unknownsRemaining", "generatedFiles", "destructiveChanges", "observedIssues"):
        if key in summary and not isinstance(summary.get(key), list):
            issues.append(f"{key} must be a list")

    for key in ("userCorrectionsCaptured", "userCorrectionSolidification", "knownGaps"):
        if key in summary and not isinstance(summary.get(key), list):
            issues.append(f"{key} must be a list")

    residual = summary.get("residualRisks")
    if residual is not None:
        if not isinstance(residual, list):
            issues.append("residualRisks must be a list")
        else:
            for index, item in enumerate(residual):
                if not isinstance(item, dict):
                    issues.append(f"residualRisks[{index}] must be an object")
                    continue
                if item.get("level") not in RISK_LEVELS:
                    issues.append(f"residualRisks[{index}].level must be one of {sorted(RISK_LEVELS)}")
                if not non_empty_string(item.get("area")):
                    issues.append(f"residualRisks[{index}].area is required")
                if not non_empty_string(item.get("detail")):
                    issues.append(f"residualRisks[{index}].detail is required")

    readiness = summary.get("reviewReadiness")
    if readiness is not None:
        if not isinstance(readiness, dict):
            issues.append("reviewReadiness must be an object")
        else:
            if readiness.get("status") not in REVIEW_READINESS_STATUSES:
                issues.append(f"reviewReadiness.status must be one of {sorted(REVIEW_READINESS_STATUSES)}")
            if not non_empty_string(readiness.get("reason")):
                issues.append("reviewReadiness.reason is required")
            focus = readiness.get("expectedReviewFocus")
            if focus is not None and (not isinstance(focus, list) or any(not non_empty_string(item) for item in focus)):
                issues.append("reviewReadiness.expectedReviewFocus must be a list of non-empty strings")

    boundary = summary.get("boundaryChecks")
    if boundary is not None:
        if not isinstance(boundary, dict):
            issues.append("boundaryChecks must be an object")
        else:
            for key, value in boundary.items():
                if not non_empty_string(key) or not non_empty_string(value):
                    issues.append("boundaryChecks must map non-empty names to non-empty status strings")
                    break

    if "overclaimPrevention" in summary and not non_empty_string(summary.get("overclaimPrevention")):
        issues.append("overclaimPrevention must be a non-empty string")

    if contract is not None:
        required = [
            item.get("command")
            for item in contract.get("verification", [])
            if isinstance(item, dict) and item.get("required") is True and non_empty_string(item.get("command"))
        ]
        status = {item.get("command"): item.get("result") for item in summary.get("verification", []) if isinstance(item, dict)}
        missing = [command for command in required if command not in status]
        non_passed = [command for command in required if status.get(command) != "passed"]
        if missing:
            issues.append(f"Summary is missing required verification: {', '.join(missing)}")
        if non_passed:
            issues.append(f"required verification is not passed: {', '.join(non_passed)}")
    return issues


def validate_changed_files_cover_diff(summary: dict[str, Any]) -> list[str]:
    try:
        paths = changed_paths()
    except RuntimeError as exc:
        return [f"failed to read changed paths: {exc}"]

    reported = changed_file_paths(summary)
    exempt = summary_exempt_patterns()
    missing = [
        path
        for path in paths
        if path not in reported and not included(path, exempt)
    ]
    if not missing:
        return []
    return [f"changedFiles is missing actual changed path: {path}" for path in missing]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate AI Change Summary.")
    parser.add_argument("summary", nargs="?")
    parser.add_argument("--contract")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.summary:
        print("Skipping summary check (no active summary provided)")
        return 0
    start = time.time()
    try:
        summary = load_json(Path(args.summary))
        contract = load_json(Path(args.contract)) if args.contract else None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Failed to read Summary or Contract: {exc}", file=sys.stderr)
        return 1

    obs = create_observability(work_item_id=summary.get("workItemId", ""))
    issues = validate_summary(summary, contract)
    issues.extend(validate_changed_files_cover_diff(summary))
    duration = elapsed_ms(start)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        obs.check_failed(check_id="aiSummary", duration_ms=duration, detail=f"{len(issues)} issue(s)")
        return 1
    print(f"ai summary check passed: {args.summary}")
    obs.check_passed(check_id="aiSummary", duration_ms=duration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
