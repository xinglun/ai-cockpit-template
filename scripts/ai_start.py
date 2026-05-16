#!/usr/bin/env python3
"""Create a new Work Item Contract and Summary skeleton."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ai_common import PROJECT_ROOT, save_json
from ai_observability import create_observability


ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"
MODES = ["investigate", "author_todo", "code", "review", "cleanup"]


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip().lower()).strip("_")
    if not normalized:
        raise ValueError("TASK cannot be empty")
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an AI Work Item skeleton.")
    parser.add_argument("--task", required=True, help="Task id, for example: add_health_check")
    parser.add_argument("--title", help="Human-readable title. Defaults to the task id.")
    parser.add_argument("--mode", default="investigate", choices=MODES)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing skeleton.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        task = slug(args.task)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    contract_path = ACTIVE_DIR / f"{task}.contract.json"
    summary_path = ACTIVE_DIR / f"{task}.summary.json"
    if not args.force and (contract_path.exists() or summary_path.exists()):
        print(f"ERROR: Work Item already exists: {task}", file=sys.stderr)
        return 1

    title = args.title or task.replace("_", " ")
    contract_rel = contract_path.relative_to(PROJECT_ROOT).as_posix()
    summary_rel = summary_path.relative_to(PROJECT_ROOT).as_posix()
    contract = {
        "contractVersion": 1,
        "workItemId": task,
        "mode": args.mode,
        "title": title,
        "scope": [contract_rel, summary_rel],
        "outOfScope": [],
        "sources": [{"path": contract_rel, "reason": "Initial Work Item skeleton."}],
        "unknowns": ["Replace this with concrete open questions, or clear it before mode code."],
        "notCodable": args.mode == "code",
        "acceptance": ["The Work Item Contract is updated for the actual task."],
        "verification": [
            {"command": f"make check-ai-contract CONTRACT={contract_rel}", "required": True},
            {"command": f"make check-ai-scope CONTRACT={contract_rel}", "required": True},
            {"command": "make check-ai-backtrack", "required": True},
            {"command": "make check-ai-coverage-guard", "required": False},
            {"command": f"make check-ai-change-summary SUMMARY={summary_rel} CONTRACT={contract_rel}", "required": True},
            {"command": f"make generate-cockpit-status CONTRACT={contract_rel} SUMMARY={summary_rel}", "required": True},
            {"command": f"make check-ai-status CONTRACT={contract_rel} SUMMARY={summary_rel}", "required": True},
        ],
        "destructiveChangePolicy": {"allowed": False, "requiresHumanApproval": True, "allowPatterns": []},
        "rollbackNote": "Revert this Work Item diff and restore related tests and docs.",
    }
    summary = {
        "workItemId": task,
        "contractPath": contract_rel,
        "changedFiles": [
            {"path": contract_rel, "reason": "Created the Work Item Contract skeleton."},
            {"path": summary_rel, "reason": "Created the AI Change Summary skeleton."},
        ],
        "sourcesUsed": [contract_rel],
        "verification": [{"command": item["command"], "result": "not_run"} for item in contract["verification"]],
        "unknownsRemaining": ["Replace this before finishing the Work Item."],
        "risk": {"level": "medium", "detail": "Initial skeleton; scope and acceptance still need task-specific review."},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
    }
    save_json(contract_path, contract)
    save_json(summary_path, summary)
    print(f"Work Item skeleton created: {task}")
    print(f"contract: {contract_rel}")
    print(f"summary: {summary_rel}")

    create_observability(work_item_id=task).work_item_started(fields={"mode": args.mode, "title": title})
    return 0


if __name__ == "__main__":
    sys.exit(main())

