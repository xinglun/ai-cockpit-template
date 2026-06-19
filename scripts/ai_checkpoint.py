#!/usr/bin/env python3
"""Print a compact checkpoint for the active Work Item."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ai_common import load_json, verification_key


def required_verification(contract: dict[str, Any]) -> list[str]:
    return [
        verification_key(item)
        for item in contract.get("verification", [])
        if isinstance(item, dict) and item.get("required") is True and verification_key(item)
    ]


def contract_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def verification_status(summary: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(summary, dict):
        return {}
    statuses: dict[str, str] = {}
    for item in summary.get("verification", []):
        if isinstance(item, dict) and verification_key(item) and isinstance(item.get("result"), str):
            statuses[verification_key(item)] = str(item["result"])
    return statuses


def review_focus(summary: dict[str, Any] | None) -> list[str]:
    if not isinstance(summary, dict):
        return []
    readiness = summary.get("reviewReadiness")
    if not isinstance(readiness, dict):
        return []
    focus = readiness.get("expectedReviewFocus")
    if not isinstance(focus, list):
        return []
    return [item for item in focus if isinstance(item, str) and item.strip()]


def next_action(contract: dict[str, Any], summary: dict[str, Any] | None) -> str:
    if contract.get("notCodable") is True:
        return "Stop coding. Resolve notCodable or record blocker/unknowns."
    unknowns = contract.get("unknowns")
    if isinstance(unknowns, list) and unknowns:
        return "Stop coding. Resolve unknowns or switch executionDecision away from continue."
    missing = [
        command
        for command in required_verification(contract)
        if verification_status(summary).get(command) != "passed"
    ]
    if missing:
        return f"Run or record required verification: {missing[0]}"
    return "Ready for final status generation and human review."


def print_list(title: str, values: list[Any]) -> None:
    print(f"\n## {title}")
    if not values:
        print("- none")
        return
    for value in values:
        print(f"- {value}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print an AI Work Item checkpoint.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--summary")
    parser.add_argument("--stage", default="manual", help="Checkpoint stage, for example before_edit or before_finish.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        contract = load_json(Path(args.contract))
        summary = load_json(Path(args.summary)) if args.summary and Path(args.summary).exists() else None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Failed to load checkpoint inputs: {exc}", file=sys.stderr)
        return 1

    print("# AI Work Item Checkpoint")
    print(f"- Stage: `{args.stage}`")
    print(f"- Work Item: `{contract.get('workItemId', '')}`")
    print(f"- Contract Hash: `{contract_hash(Path(args.contract))}`")
    print(f"- Mode: `{contract.get('mode', '')}`")
    print(f"- notCodable: `{contract.get('notCodable')}`")
    print(f"- Execution Decision: `{contract.get('executionDecision', {}).get('status', '')}`")
    acceptance = contract.get("acceptance", []) if isinstance(contract.get("acceptance"), list) else []
    unknowns = contract.get("unknowns", []) if isinstance(contract.get("unknowns"), list) else []
    required = required_verification(contract)
    status = verification_status(summary)
    passed_required = [command for command in required if status.get(command) == "passed"]
    print(f"- Acceptance Count: `{len(acceptance)}`")
    print(f"- Unknown Count: `{len(unknowns)}`")
    print(f"- Required Checks: `{len(required)}`")
    print(f"- Required Checks Passed: `{len(passed_required)}`")

    print_list("Scope", contract.get("scope", []) if isinstance(contract.get("scope"), list) else [])
    print_list("Out Of Scope", contract.get("outOfScope", []) if isinstance(contract.get("outOfScope"), list) else [])
    print_list("Unknowns", unknowns)
    print_list("Acceptance", acceptance)

    print("\n## Required Verification")
    if not required:
        print("- none")
    for command in required:
        print(f"- `{command}`: {status.get(command, 'not_recorded')}")

    print_list("Review Focus", review_focus(summary))
    print(f"\n## Next Action\n- {next_action(contract, summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
