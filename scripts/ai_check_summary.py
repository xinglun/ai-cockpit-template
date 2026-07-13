#!/usr/bin/env python3
"""Validate an AI Change Summary against a Work Item Contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

from ai_common import (
    PROJECT_ROOT,
    changed_paths,
    contains_machine_path,
    included,
    load_json,
    non_empty_string,
    render_check_command,
    simple_yaml_lists,
    verification_key,
    validate_scenario_coverage,
)
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
ALLOWED_FIELDS = set(REQUIRED_FIELDS) | {
    "boundaryChecks",
    "checkpointEvidence",
    "checkpointReview",
    "followUps",
    "generatedFiles",
    "guidelinesCompliance",
    "knownGaps",
    "issuesObserved",
    "overclaimPrevention",
    "residualRisks",
    "reviewReadiness",
    "scenarioCoverage",
    "sourcesUsed",
    "summaryVersion",
    "title",
    "unverifiedScenarios",
    "userCorrectionSolidification",
    "userCorrectionsCaptured",
    "intentAlignment",
}
RESULTS = {"passed", "failed", "not_run"}
RISK_LEVELS = {"low", "medium", "high"}
REVIEW_READINESS_STATUSES = {"not_ready", "ready", "ready_with_risks", "blocked"}
INTENT_ALIGNMENT_BOOL_KEYS = {"problemResolved", "constraintsRespected", "nonGoalsAvoided"}
INTENT_ALIGNMENT_STRING_KEYS = {"rationaleValidated"}


def intent_alignment_is_compat_evidence_key(key: str) -> bool:
    """Return True for legacy archive evidence aliases.

    Older archived summaries used ``*Evidence`` field names for the same
    intent-alignment facts. Keep those readable without forcing archive rewrites.
    """
    return key.endswith("Evidence")


def changed_file_paths(summary: dict[str, Any]) -> set[str]:
    changed = summary.get("changedFiles")
    if not isinstance(changed, list):
        return set()
    return {
        str(item["path"])
        for item in changed
        if isinstance(item, dict) and non_empty_string(item.get("path"))
    }


def summary_exempt_patterns() -> list[str]:
    policy_lists = simple_yaml_lists(SCOPE_POLICY)
    return policy_lists.get("allowAlways", [])


def validate_summary(
    summary: dict[str, Any],
    contract: dict[str, Any] | None,
    *,
    expected_contract_hash: str = "",
    contract_path: str = "",
    summary_path: str = "",
) -> list[str]:
    issues: list[str] = []
    for key in REQUIRED_FIELDS:
        if key not in summary:
            issues.append(f"missing field: {key}")

    if summary.get("summaryVersion") != 2:
        issues.append("summaryVersion must be 2")

    for key in summary:
        if key not in ALLOWED_FIELDS:
            issues.append(f"unknown field: {key}")

    if contract is not None and summary.get("workItemId") != contract.get("workItemId"):
        issues.append("workItemId does not match the Contract")

    if contract_path:
        expected_contract_path = Path(contract_path).as_posix()
        if summary.get("contractPath") != expected_contract_path:
            issues.append("contractPath does not match the Contract path")

    if summary_path:
        summary_file = Path(summary_path)
        stem = summary_file.name.removesuffix(".summary.json")
        if stem and summary.get("workItemId") != stem:
            issues.append("workItemId does not match the Summary filename")

    changed = summary.get("changedFiles")
    if not isinstance(changed, list) or not changed:
        issues.append("changedFiles must contain at least one item")
    elif any(
        not isinstance(item, dict)
        or not non_empty_string(item.get("path"))
        or not non_empty_string(item.get("reason"))
        for item in changed
    ):
        issues.append("changedFiles must be a list of objects with path and reason")

    verification = summary.get("verification")
    if not isinstance(verification, list) or not verification:
        issues.append("verification must contain at least one item")
    else:
        for index, item in enumerate(verification):
            if not isinstance(item, dict):
                issues.append(f"verification[{index}] must be an object")
                continue
            key = verification_key(item)
            if not key:
                issues.append(f"verification[{index}] requires check or command")
            if isinstance(contract, dict) and contract.get("contractVersion") == 2:
                if not non_empty_string(item.get("check")):
                    issues.append(f"verification[{index}].check is required for contractVersion 2")
                else:
                    try:
                        expected_command, _ = render_check_command(
                            item["check"],
                            contract_path=item.get("executionContractPath", contract_path),
                            summary_path=item.get("executionSummaryPath", summary_path),
                        )
                        if (
                            item.get("command") != expected_command
                            and item.get("result") == "passed"
                        ):
                            issues.append(
                                f"verification[{index}].command does not match registered check"
                            )
                    except ValueError as exc:
                        issues.append(f"verification[{index}]: {exc}")
            if item.get("result") not in RESULTS:
                issues.append(f"verification[{index}].result must be one of {sorted(RESULTS)}")
            if item.get("result") == "passed" and (
                not isinstance(contract, dict) or contract.get("contractVersion") == 2
            ):
                if item.get("runner") != "ai_finish":
                    issues.append(f"verification[{index}] passed result requires runner ai_finish")
                if not non_empty_string(item.get("executedAt")):
                    issues.append(f"verification[{index}].executedAt is required for passed result")
                if not isinstance(item.get("exitCode"), int) or item.get("exitCode") != 0:
                    issues.append(f"verification[{index}].exitCode must be 0 for passed result")
                duration = item.get("durationMs")
                if not isinstance(duration, int) or duration < 0:
                    issues.append(
                        f"verification[{index}].durationMs must be a non-negative integer"
                    )
                digest = item.get("outputDigest")
                if (
                    not non_empty_string(digest)
                    or len(str(digest)) != 64
                    or any(ch not in "0123456789abcdef" for ch in str(digest))
                ):
                    issues.append(
                        f"verification[{index}].outputDigest must be a SHA-256 hex digest"
                    )
                if isinstance(contract, dict) and contract.get("contractVersion") == 2:
                    command = item.get("command", "")
                    command_hash = hashlib.sha256(
                        " ".join(command.split()).encode("utf-8")
                    ).hexdigest()
                    if item.get("commandHash") != command_hash:
                        issues.append(f"verification[{index}].commandHash does not match command")
                    if (
                        expected_contract_hash
                        and item.get("contractHash") != expected_contract_hash
                    ):
                        issues.append(f"verification[{index}].contractHash does not match Contract")
                    for path_key in ("executionContractPath", "executionSummaryPath"):
                        if (
                            not non_empty_string(item.get(path_key))
                            or Path(item[path_key]).is_absolute()
                        ):
                            issues.append(
                                f"verification[{index}].{path_key} must be a repository-relative path"
                            )
                    commit_sha = item.get("commitSha")
                    if (
                        not non_empty_string(commit_sha)
                        or len(str(commit_sha)) not in {40, 64}
                        or any(ch not in "0123456789abcdef" for ch in str(commit_sha))
                    ):
                        issues.append(f"verification[{index}].commitSha must be a Git object id")
                    worktree_digest = item.get("worktreeDigest")
                    if worktree_digest is not None and (
                        not non_empty_string(worktree_digest)
                        or len(str(worktree_digest)) != 64
                        or any(ch not in "0123456789abcdef" for ch in str(worktree_digest))
                    ):
                        issues.append(
                            f"verification[{index}].worktreeDigest must be a SHA-256 hex digest"
                        )

    risk = summary.get("risk")
    if not isinstance(risk, dict):
        issues.append("risk must be an object")
    else:
        if risk.get("level") not in RISK_LEVELS:
            issues.append(f"risk.level must be one of {sorted(RISK_LEVELS)}")
        if not non_empty_string(risk.get("detail")):
            issues.append("risk.detail is required")

    for key in (
        "sourcesUsed",
        "unknownsRemaining",
        "generatedFiles",
        "destructiveChanges",
        "observedIssues",
        "guidelinesCompliance",
        "followUps",
        "unverifiedScenarios",
    ):
        if key in summary and not isinstance(summary.get(key), list):
            issues.append(f"{key} must be a list")

    for key in ("userCorrectionsCaptured", "userCorrectionSolidification", "knownGaps"):
        if key in summary and not isinstance(summary.get(key), list):
            issues.append(f"{key} must be a list")

    checkpoints = summary.get("checkpointEvidence")
    if checkpoints is not None:
        if not isinstance(checkpoints, list):
            issues.append("checkpointEvidence must be a list")
        else:
            for index, item in enumerate(checkpoints):
                if not isinstance(item, dict):
                    issues.append(f"checkpointEvidence[{index}] must be an object")
                    continue
                if not non_empty_string(item.get("stage")):
                    issues.append(f"checkpointEvidence[{index}].stage is required")
                if "recorded" in item and not isinstance(item.get("recorded"), bool):
                    issues.append(f"checkpointEvidence[{index}].recorded must be boolean")
                if "detail" in item and not isinstance(item.get("detail"), str):
                    issues.append(f"checkpointEvidence[{index}].detail must be a string")
                if "contractHash" in item and not non_empty_string(item.get("contractHash")):
                    issues.append(
                        f"checkpointEvidence[{index}].contractHash must be a non-empty string"
                    )
                for metric in (
                    "acceptanceCount",
                    "unknownCount",
                    "requiredChecks",
                    "requiredChecksPassed",
                ):
                    if metric in item and not isinstance(item.get(metric), int):
                        issues.append(f"checkpointEvidence[{index}].{metric} must be integer")

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
                    issues.append(
                        f"residualRisks[{index}].level must be one of {sorted(RISK_LEVELS)}"
                    )
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
                issues.append(
                    f"reviewReadiness.status must be one of {sorted(REVIEW_READINESS_STATUSES)}"
                )
            if not non_empty_string(readiness.get("reason")):
                issues.append("reviewReadiness.reason is required")
            focus = readiness.get("expectedReviewFocus")
            if focus is not None and (
                not isinstance(focus, list) or any(not non_empty_string(item) for item in focus)
            ):
                issues.append(
                    "reviewReadiness.expectedReviewFocus must be a list of non-empty strings"
                )

    issues.extend(validate_intent_alignment(summary))

    boundary = summary.get("boundaryChecks")
    if boundary is not None:
        if not isinstance(boundary, dict):
            issues.append("boundaryChecks must be an object")
        else:
            for key, value in boundary.items():
                if not non_empty_string(key) or not non_empty_string(value):
                    issues.append(
                        "boundaryChecks must map non-empty names to non-empty status strings"
                    )
                    break

    if "overclaimPrevention" in summary and not non_empty_string(
        summary.get("overclaimPrevention")
    ):
        issues.append("overclaimPrevention must be a non-empty string")

    issues.extend(validate_scenario_coverage(summary.get("scenarioCoverage")))

    def scan_machine_paths(value: Any, location: str) -> None:
        if isinstance(value, str) and contains_machine_path(value):
            issues.append(f"{location} contains a machine-specific path")
        elif isinstance(value, dict):
            for key, child in value.items():
                scan_machine_paths(child, f"{location}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan_machine_paths(child, f"{location}[{index}]")

    scan_machine_paths(summary, "summary")

    if contract is not None:
        required = [
            verification_key(item)
            for item in contract.get("verification", [])
            if isinstance(item, dict) and item.get("required") is True and verification_key(item)
        ]
        status = {
            verification_key(item): item.get("result")
            for item in summary.get("verification", [])
            if isinstance(item, dict)
        }
        missing = [command for command in required if command not in status]
        non_passed = [command for command in required if status.get(command) != "passed"]
        if missing:
            issues.append(f"Summary is missing required verification: {', '.join(missing)}")
        if non_passed:
            issues.append(f"required verification is not passed: {', '.join(non_passed)}")
    return issues


def validate_intent_alignment(summary: dict[str, Any]) -> list[str]:
    """Validate the optional Summary intentAlignment section.

    The section may be absent, null, empty, partially populated, or complete.
    Legacy archived summaries may also use ``*Evidence`` aliases for the same
    fields, and those remain accepted for backward compatibility.
    """
    issues: list[str] = []
    alignment = summary.get("intentAlignment")
    if alignment is None:
        return issues
    if not isinstance(alignment, dict):
        issues.append("intentAlignment must be an object")
        return issues

    for key in alignment:
        if (
            key not in INTENT_ALIGNMENT_BOOL_KEYS | INTENT_ALIGNMENT_STRING_KEYS
            and not intent_alignment_is_compat_evidence_key(key)
        ):
            issues.append(f"intentAlignment.{key} is not a recognized field")

    for key in INTENT_ALIGNMENT_BOOL_KEYS:
        value = alignment.get(key)
        if value is not None and not isinstance(value, bool):
            issues.append(f"intentAlignment.{key} must be boolean when provided")

    for key, value in alignment.items():
        if key not in INTENT_ALIGNMENT_STRING_KEYS and not intent_alignment_is_compat_evidence_key(
            key
        ):
            continue
        if value is not None and not non_empty_string(value):
            issues.append(f"intentAlignment.{key} must be a non-empty string when provided")

    return issues


def validate_changed_files_cover_diff(
    summary: dict[str, Any], contract: dict[str, Any] | None = None
) -> list[str]:
    try:
        paths = changed_paths(contract)
    except RuntimeError as exc:
        return [f"failed to read changed paths: {exc}"]

    reported = changed_file_paths(summary)
    exempt = summary_exempt_patterns()
    missing = [path for path in paths if path not in reported and not included(path, exempt)]
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
    expected_hash = (
        hashlib.sha256(Path(args.contract).read_bytes()).hexdigest() if args.contract else ""
    )
    issues = validate_summary(
        summary,
        contract,
        expected_contract_hash=expected_hash,
        contract_path=args.contract or "",
        summary_path=args.summary,
    )
    issues.extend(validate_changed_files_cover_diff(summary, contract))
    duration = elapsed_ms(start)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        obs.check_failed(
            check_id="aiSummary", duration_ms=duration, detail=f"{len(issues)} issue(s)"
        )
        return 1
    print(f"ai summary check passed: {args.summary}")
    obs.check_passed(check_id="aiSummary", duration_ms=duration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
