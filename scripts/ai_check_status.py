#!/usr/bin/env python3
"""Verify current_status.md matches the active Contract and Summary."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from ai_common import load_json
from ai_observability import create_observability, elapsed_ms


REQUIRED_FIELDS = ("workItemId", "mode")


def required_commands(contract: dict[str, Any]) -> list[str]:
    return [
        item.get("command")
        for item in contract.get("verification", [])
        if isinstance(item, dict) and item.get("required") is True and isinstance(item.get("command"), str)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Cockpit current status.")
    parser.add_argument("status", nargs="?")
    parser.add_argument("--contract")
    parser.add_argument("--summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.contract or not args.summary:
        print("Skipping status check (no active contract/summary provided)")
        return 0
    start = time.time()
    try:
        contract = load_json(Path(args.contract))
        summary = load_json(Path(args.summary))
        status = Path(args.status).read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Failed to validate Cockpit status: {exc}", file=sys.stderr)
        return 1

    obs = create_observability(work_item_id=contract.get("workItemId", ""))
    issues: list[str] = []
    for key in REQUIRED_FIELDS:
        value = contract.get(key)
        if isinstance(value, str) and f"`{value}`" not in status:
            issues.append(f"status is missing Contract {key}: {value}")

    if f"- Contract Path: `{args.contract}`" not in status:
        issues.append("status Contract Path does not match")
    if f"- Summary Path: `{args.summary}`" not in status:
        issues.append("status Summary Path does not match")
    if "- State: `ready_for_review`" not in status:
        issues.append("status is not ready_for_review")
    blocking_section = status.split("## Required Checks", 1)[0]
    if "## Blocking" not in blocking_section or "- none" not in blocking_section:
        issues.append("Blocking section is not none")

    verification_status = {item.get("command"): item.get("result") for item in summary.get("verification", []) if isinstance(item, dict)}
    for command in required_commands(contract):
        expected = f"- `{command}`: passed"
        if verification_status.get(command) != "passed":
            issues.append(f"Summary required check is not passed: {command}")
        if expected not in status:
            issues.append(f"status does not show required check as passed: {command}")

    duration = elapsed_ms(start)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        obs.check_failed(check_id="aiStatusCheck", duration_ms=duration, detail=f"{len(issues)} issue(s)")
        return 1
    print(f"cockpit status check passed: {args.status}")
    obs.check_passed(check_id="aiStatusCheck", duration_ms=duration)
    return 0


if __name__ == "__main__":
    sys.exit(main())

