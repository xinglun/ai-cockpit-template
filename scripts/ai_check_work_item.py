#!/usr/bin/env python3
"""Validate the minimum Work Item Contract structure."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from ai_common import load_json, non_empty_string
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
ALLOWED_FIELDS = set(REQUIRED_FIELDS) | {"destructiveChangePolicy"}
MODES = {"investigate", "author_todo", "code", "review", "cleanup"}


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
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            issues.append(f"verification[{index}] must be an object")
            continue
        if not non_empty_string(item.get("command")):
            issues.append(f"verification[{index}].command is required")
        if not isinstance(item.get("required"), bool):
            issues.append(f"verification[{index}].required must be boolean")
    return issues


def validate_contract(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in REQUIRED_FIELDS:
        if key not in data:
            issues.append(f"missing field: {key}")
    for key in data:
        if key not in ALLOWED_FIELDS:
            issues.append(f"unknown field: {key}")

    if data.get("contractVersion") != 1:
        issues.append("contractVersion must be 1")
    if data.get("mode") not in MODES:
        issues.append(f"mode must be one of {sorted(MODES)}")
    for key in ("workItemId", "title", "rollbackNote"):
        if key in data and not non_empty_string(data.get(key)):
            issues.append(f"{key} must be a non-empty string")

    issues.extend(validate_string_list(data, "scope", allow_empty=False))
    issues.extend(validate_string_list(data, "outOfScope", allow_empty=True))
    issues.extend(validate_string_list(data, "unknowns", allow_empty=True))
    issues.extend(validate_string_list(data, "acceptance", allow_empty=False))
    issues.extend(validate_sources(data))
    issues.extend(validate_verification(data))

    if not isinstance(data.get("notCodable"), bool):
        issues.append("notCodable must be boolean")
    if data.get("mode") == "code" and data.get("notCodable"):
        issues.append("mode code cannot run with notCodable true")
    if data.get("mode") == "code" and data.get("unknowns"):
        issues.append("mode code cannot run while unknowns remain")
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

