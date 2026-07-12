#!/usr/bin/env python3
"""Verify current_status.md matches the active Contract and Summary."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from ai_common import load_json, verification_key
from ai_observability import create_observability, elapsed_ms
from ai_generate_status import BACKTRACK_REPORT, DEFAULT_LOG_PATH, DEFAULT_RETRY_THRESHOLD, load_preflight_review, project_relative, status_for
from ai_governance_compression import derive_governance_status, render_active_status
from ai_check_diff_ownership import counts as ownership_counts_for, preview as ownership_preview


REQUIRED_FIELDS = ("workItemId", "mode")


def required_commands(contract: dict[str, Any]) -> list[str]:
    return [
        verification_key(item)
        for item in contract.get("verification", [])
        if isinstance(item, dict) and item.get("required") is True and verification_key(item)
    ]


def normalize_generated_at(text: str) -> str:
    return re.sub(r"- Generated At: `[^`]+`", "- Generated At: `<timestamp>`", text)


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

    state, blockers = status_for(
        contract,
        summary,
        retry_threshold=DEFAULT_RETRY_THRESHOLD,
        observability_log=DEFAULT_LOG_PATH,
    )
    model = derive_governance_status(contract, summary)
    backtrack = load_json(BACKTRACK_REPORT) if BACKTRACK_REPORT.exists() else None
    preflight_review = load_preflight_review(contract, Path(args.contract))
    ownership_counts = ownership_counts_for(ownership_preview(contract=contract))
    if state == "blocked" and blockers and blockers[0].startswith("retry circuit breaker"):
        model = {
            **model,
            "recommendation": "blocked",
            "decisionDrivers": blockers,
            "evidence": {
                **model["evidence"],
                "summary": model["evidence"].get("summary", []) + [blockers[0]],
            },
        }
    expected = render_active_status(
        model,
        work_item_id=str(contract.get("workItemId", "")),
        mode=str(contract.get("mode", "")),
        contract_path=args.contract,
        summary_path=args.summary,
        generated_at="<timestamp>",
        backtrack_report=project_relative(BACKTRACK_REPORT) if isinstance(backtrack, dict) else None,
        backtrack_status=(backtrack.get("status") if isinstance(backtrack, dict) and isinstance(backtrack.get("status"), str) else None),
        backtrack_items=(backtrack.get("items") if isinstance(backtrack, dict) and isinstance(backtrack.get("items"), list) else None),
        preflight_review=preflight_review,
        ownership_counts=ownership_counts,
    )

    if normalize_generated_at(status) != normalize_generated_at(expected):
        issues.append("status content does not match compressed governance model")

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
