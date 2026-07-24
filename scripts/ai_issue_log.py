#!/usr/bin/env python3
"""Validate structured issue-log records without exposing sensitive values."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

STAGES = {"preflight", "implementation", "verification", "pr", "merge", "closure"}
SEVERITIES = {"informational", "warning", "needs_human_confirmation", "blocked"}
STATUSES = {"open", "resolved", "accepted_residual_risk", "blocked"}
REQUIRED = {
    "issueId",
    "workItem",
    "stage",
    "observedAt",
    "severity",
    "title",
    "evidence",
    "impact",
    "owner",
    "containment",
    "status",
    "resolution",
    "verificationRefs",
    "affectsCompletionClaim",
}
SENSITIVE = re.compile(
    r"(?:"
    + r"-" * 5
    + r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"
    + r"-" * 5
    + r"|\b(?:gh[pousr]|sk)-[A-Za-z0-9_-]{8,}|\b(?:api[_ -]?key|token|password|secret)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


def _contains_sensitive(value: Any) -> bool:
    if isinstance(value, str):
        return bool(SENSITIVE.search(value))
    if isinstance(value, dict):
        return any(_contains_sensitive(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_sensitive(item) for item in value)
    return False


def validate_issue_record(record: dict[str, Any]) -> list[str]:
    """Return safe, non-echoing validation issues for one record."""

    issues: list[str] = []
    missing = sorted(REQUIRED - record.keys())
    if missing:
        issues.append(f"missing required fields: {', '.join(missing)}")
        return issues
    if not isinstance(record["issueId"], str) or not re.fullmatch(
        r"IW-\d{8}-\d{3}", record["issueId"]
    ):
        issues.append("issueId must match IW-YYYYMMDD-NNN")
    if not isinstance(record["stage"], str) or record["stage"] not in STAGES:
        issues.append("stage is invalid")
    if not isinstance(record["severity"], str) or record["severity"] not in SEVERITIES:
        issues.append("severity is invalid")
    if not isinstance(record["status"], str) or record["status"] not in STATUSES:
        issues.append("status is invalid")
    for field in ("workItem", "observedAt", "title", "impact", "owner", "containment"):
        if not isinstance(record[field], str) or not record[field].strip():
            issues.append(f"{field} must be a non-empty string")
    if not isinstance(record["evidence"], list) or not record["evidence"]:
        issues.append("evidence must contain at least one reference")
    elif not all(isinstance(item, str) and item.strip() for item in record["evidence"]):
        issues.append("evidence references must be non-empty strings")
    if not isinstance(record["verificationRefs"], list) or not all(
        isinstance(item, str) and item.strip() for item in record["verificationRefs"]
    ):
        issues.append("verificationRefs must be a list of non-empty strings")
    if not isinstance(record["affectsCompletionClaim"], bool):
        issues.append("affectsCompletionClaim must be boolean")
    if record["status"] == "resolved" and (
        not isinstance(record["resolution"], str) or not record["resolution"].strip()
    ):
        issues.append("resolved records require a resolution")
    if record["status"] != "resolved" and record["resolution"] is not None:
        issues.append("unresolved records must have a null resolution")
    if _contains_sensitive(record):
        issues.append("record contains sensitive material")
    return issues


def validate_transition(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """Ensure a later record only advances an issue's state."""

    issues = validate_issue_record(current)
    if previous.get("issueId") != current.get("issueId"):
        issues.append("append-only transition must retain issueId")
    if previous.get("status") == "resolved" and current.get("status") != "resolved":
        issues.append("append-only records cannot reopen a resolved issue")
    if current.get("status") == "resolved" and not current.get("verificationRefs"):
        issues.append("resolved transitions require verificationRefs")
    return issues


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("record must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    try:
        record = _load(args.record)
        issues = (
            validate_transition(_load(args.previous), record)
            if args.previous
            else validate_issue_record(record)
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"issue log validation error: {exc}", file=sys.stderr)
        return 2
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print("issue log record valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
