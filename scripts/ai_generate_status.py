#!/usr/bin/env python3
"""Generate .ai/cockpit/current_status.md from a Contract and Summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_common import PROJECT_ROOT, changed_paths, load_json
from ai_check_diff_ownership import counts as ownership_counts_for, preview as ownership_preview
from ai_observability import DEFAULT_LOG_PATH, create_observability
from ai_governance_compression import derive_governance_status, render_active_status


DEFAULT_OUTPUT = PROJECT_ROOT / ".ai" / "cockpit" / "current_status.md"
BACKTRACK_REPORT = PROJECT_ROOT / "target" / "ai_backtrack_report.json"
DEFAULT_RETRY_THRESHOLD = 5


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def consecutive_failure_count(work_item_id: str, log_path: Path = DEFAULT_LOG_PATH) -> int:
    if not work_item_id or not log_path.exists():
        return 0
    count = 0
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    for raw in reversed(lines):
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("workItemId") != work_item_id:
            continue
        if event.get("eventType") == "check_failed":
            count += 1
            continue
        if event.get("eventType") == "check_passed":
            break
    return count


def status_for(
    contract: dict[str, Any],
    summary: dict[str, Any] | None,
    *,
    retry_threshold: int,
    observability_log: Path,
) -> tuple[str, list[str]]:
    work_item_id = contract.get("workItemId", "")
    if isinstance(work_item_id, str) and retry_threshold > 0:
        failures = consecutive_failure_count(work_item_id, observability_log)
        if failures >= retry_threshold:
            return "blocked", [
                f"retry circuit breaker: consecutive check failures {failures}/{retry_threshold}"
            ]

    model = derive_governance_status(contract, summary)
    return model["recommendation"], model["decisionDrivers"]


def unresolved_ownership_count(ownership_counts: dict[str, int] | None) -> int:
    if not isinstance(ownership_counts, dict):
        return 0
    return sum(
        int(ownership_counts.get(state, 0))
        for state in ("unowned", "ambiguous", "out_of_scope", "approval_required")
    )


def apply_ownership_reconciliation(
    model: dict[str, Any],
    ownership_counts: dict[str, int] | None,
) -> dict[str, Any]:
    unresolved = unresolved_ownership_count(ownership_counts)
    if unresolved <= 0:
        return model

    updated_model = dict(model)
    decision_drivers = [
        driver for driver in model.get("decisionDrivers", []) if isinstance(driver, str)
    ]
    ownership_driver = f"diff ownership unresolved: {unresolved}"
    if ownership_driver not in decision_drivers:
        decision_drivers.append(ownership_driver)
    if updated_model.get("recommendation") in {"ready_for_review", "ready_with_risks"}:
        updated_model["recommendation"] = "needs_investigation"
    updated_model["decisionDrivers"] = decision_drivers
    return updated_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate AI Cockpit current status.")
    parser.add_argument("contract", nargs="?")
    parser.add_argument("--summary")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--observability-log", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--retry-threshold", type=int, default=DEFAULT_RETRY_THRESHOLD)
    parser.add_argument(
        "--no-active", action="store_true", help="Generate a no-active-work-item status."
    )
    return parser.parse_args()


def repository_changes_for_status(output: Path) -> list[str]:
    status_path = project_relative(output)
    return sorted(
        path
        for path in changed_paths()
        if path != status_path and not path.startswith(".ai/work-items/archive/")
    )


def default_preflight_report_path() -> Path:
    return PROJECT_ROOT / "target" / "ai_preflight_review.json"


def no_active_worktree_state(output: Path) -> tuple[str, int, str]:
    paths = repository_changes_for_status(output)
    count = len(paths)
    if count == 0:
        return "absent", 0, "clean"
    return "present", count, "ambiguous"


def load_preflight_review(
    contract: dict[str, Any],
    contract_path: Path,
    report_path: Path | None = None,
) -> dict[str, Any] | None:
    report_path = report_path or default_preflight_report_path()
    if not report_path.exists():
        return None
    try:
        report = load_json(report_path)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(report, dict):
        return None
    if report.get("workItemId") != contract.get("workItemId"):
        return None
    expected_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()[:16]
    if report.get("contractHash") != expected_hash:
        return None
    if not isinstance(report.get("status"), str) or not isinstance(
        report.get("recommendation"), str
    ):
        return None
    return report


def write_no_active_status(output: Path) -> None:
    worktree_state, worktree_count, ownership_preview_state = no_active_worktree_state(output)
    lines = [
        "---",
        "title: AI Cockpit Current Status",
        "generated: true",
        "---",
        "",
        "# AI Cockpit Current Status",
        "",
        "This file is generated by `scripts/ai_generate_status.py`. Do not update it by hand.",
        "",
        f"- Generated At: `{datetime.now(timezone.utc).isoformat()}`",
        "- Task: `none`",
        "- Mode: `none`",
        "- State: `no_active_work_item`",
        "- Contract Path: ``",
        "- Summary Path: ``",
        f"- Worktree Changes: `{worktree_state}`",
        f"- Worktree Change Count: `{worktree_count}`",
        f"- Ownership Preview: `{ownership_preview_state}`",
        "",
        "## Blocking",
        "",
        "- none",
        "",
        "## Required Checks",
        "",
        "- none",
        "",
        "## Changed Files",
        "",
        "- none",
        "",
        "No-active status intentionally excludes transient worktree changes. Use `make check-ai-diff-ownership` for a local preview and `make check-ai-pr AI_BASE_COMMIT=<merge-base>` for final PR ownership.",
        "",
        "",
        "## Backtrack",
        "",
        "- Status: `not_run`",
        "",
        "## Next Action",
        "",
        "- run `make check-ai-diff-ownership`, then verify PR ownership or create a Work Item with `make ai-start TASK=<task>` before editing",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_active_status(
    contract_path: Path,
    summary_path: Path | None,
    *,
    output: Path = DEFAULT_OUTPUT,
    observability_log: Path = DEFAULT_LOG_PATH,
    retry_threshold: int = DEFAULT_RETRY_THRESHOLD,
    announce: bool = True,
) -> None:
    try:
        contract = load_json(contract_path)
        summary = load_json(summary_path) if summary_path and summary_path.exists() else None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Failed to generate Cockpit status: {exc}") from exc

    state, blockers = status_for(
        contract,
        summary,
        retry_threshold=retry_threshold,
        observability_log=observability_log,
    )
    backtrack = load_json(BACKTRACK_REPORT) if BACKTRACK_REPORT.exists() else None
    preflight_review = load_preflight_review(contract, contract_path)
    ownership_preview_items = [
        item
        for item in ownership_preview(contract=contract)
        if item.path != project_relative(output)
    ]
    ownership_counts = ownership_counts_for(ownership_preview_items)
    model = apply_ownership_reconciliation(
        derive_governance_status(contract, summary), ownership_counts
    )
    if state == "blocked" and blockers and blockers[0].startswith("retry circuit breaker"):
        decision_drivers = list(model.get("decisionDrivers", []))
        for blocker in blockers:
            if blocker not in decision_drivers:
                decision_drivers.append(blocker)
        model = {
            **model,
            "recommendation": "blocked",
            "decisionDrivers": decision_drivers,
            "evidence": {
                **model["evidence"],
                "summary": model["evidence"].get("summary", []) + [blockers[0]],
            },
        }

    status_text = render_active_status(
        model,
        work_item_id=str(contract.get("workItemId", "")),
        mode=str(contract.get("mode", "")),
        contract_path=project_relative(contract_path),
        summary_path=project_relative(summary_path) if summary_path else "",
        generated_at=datetime.now(timezone.utc).isoformat(),
        backtrack_report=project_relative(BACKTRACK_REPORT) if BACKTRACK_REPORT.exists() else None,
        backtrack_status=(
            backtrack.get("status")
            if isinstance(backtrack, dict) and isinstance(backtrack.get("status"), str)
            else None
        ),
        backtrack_items=(
            backtrack.get("items")
            if isinstance(backtrack, dict) and isinstance(backtrack.get("items"), list)
            else None
        ),
        preflight_review=preflight_review,
        ownership_counts=ownership_counts,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(status_text, encoding="utf-8")
    if announce:
        print(f"cockpit status generated: {output}")

    create_observability(work_item_id=contract.get("workItemId", "")).status_generated(
        state=state,
        output_path=project_relative(output),
        fields={
            "blockers": len(blockers),
            "changedFiles": len(summary.get("changedFiles", []))
            if isinstance(summary, dict)
            else 0,
        },
    )


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    if args.no_active or not args.contract:
        write_no_active_status(output)
        print(f"cockpit status generated (no active Work Item): {output}")
        return 0
    try:
        write_active_status(
            Path(args.contract),
            Path(args.summary) if args.summary else None,
            output=output,
            observability_log=Path(args.observability_log),
            retry_threshold=args.retry_threshold,
        )
    except (RuntimeError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
