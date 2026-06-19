#!/usr/bin/env python3
"""Create a new Work Item Contract and Summary skeleton."""

from __future__ import annotations

import argparse
import re
import sys
from ai_common import PROJECT_ROOT, capture_dirty_baseline, current_head, save_json
from ai_check_status_consistency import DEFAULT_STATUS, validate_status_consistency
from ai_generate_status import write_active_status, write_no_active_status
from ai_observability import create_observability


ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"
MODES = ["investigate", "author_todo", "code", "review", "cleanup"]
JOURNEYS = ["feature", "bugfix", "refactor", "cleanup"]
DEFAULT_CHECKPOINT_STAGES = ["before_edit", "before_finish"]
DEFAULT_VERIFICATION_CHECKS = [
    "aiWorkItem", "aiScope", "aiGuards", "aiCheckpoint", "aiAgentRisk",
    "aiReviewPolicy", "aiBacktrack", "aiCoverage", "aiGuidelines", "aiSummary",
    "aiStatus", "aiStatusCheck", "aiStatusConsistency", "quality",
]


def default_verification() -> list[dict[str, object]]:
    return [{"check": check, "required": True} for check in DEFAULT_VERIFICATION_CHECKS]


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
    parser.add_argument("--journey", default="feature", choices=JOURNEYS, help="Work journey preset.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing skeleton.")
    return parser.parse_args()


def refresh_stale_no_active_status(issues: list[str]) -> list[str]:
    stale_message = "cockpit status Changed Files do not match current Git changes; run `make repair-ai-status`"
    if issues == [stale_message]:
        write_no_active_status(DEFAULT_STATUS)
        return validate_status_consistency()
    return issues


def main() -> int:
    args = parse_args()
    try:
        task = slug(args.task)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    consistency_issues = refresh_stale_no_active_status(validate_status_consistency())
    if consistency_issues:
        for issue in consistency_issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        print(
            "ERROR: fix Work Item lifecycle/status consistency before creating a new Work Item. "
            "Run `make repair-ai-status` when the active files are paired; otherwise clean up active Work Item files manually.",
            file=sys.stderr,
        )
        return 1

    contract_path = ACTIVE_DIR / f"{task}.contract.json"
    summary_path = ACTIVE_DIR / f"{task}.summary.json"
    if not args.force and (contract_path.exists() or summary_path.exists()):
        print(f"ERROR: Work Item already exists: {task}", file=sys.stderr)
        return 1

    title = args.title or task.replace("_", " ")
    base_commit = current_head()
    if not base_commit:
        print("ERROR: ai-start requires an initial Git commit so baseCommit is trustworthy.", file=sys.stderr)
        return 1
    baseline_dirty_paths = capture_dirty_baseline()
    contract_rel = contract_path.relative_to(PROJECT_ROOT).as_posix()
    summary_rel = summary_path.relative_to(PROJECT_ROOT).as_posix()

    # Journey configurations
    journey = args.journey
    acceptance_criteria = ["The Work Item Contract is updated for the actual task."]
    guidelines_list = []
    out_of_scope_list = []
    destructive_change_policy = {"allowed": False, "requiresHumanApproval": True, "allowPatterns": []}

    if journey == "feature":
        acceptance_criteria.extend([
            "The new feature is implemented according to requirements.",
            "Unit tests are added to verify the new feature.",
            "User documentation or comments are updated."
        ])
        guidelines_list.extend([
            "New public APIs must be documented.",
            "Do not import internal modules from other features."
        ])
    elif journey == "bugfix":
        acceptance_criteria.extend([
            "The bug is reproduced by a test case.",
            "The fix resolves the bug and the test passes.",
            "No regression is introduced in existing functionality."
        ])
        guidelines_list.extend([
            "Fix must target the root cause, not just the symptom.",
            "Avoid side effects on other components."
        ])
    elif journey == "refactor":
        acceptance_criteria.extend([
            "Code structural changes are completed without changing functional behavior.",
            "All existing unit tests pass without modifications.",
            "API backwards compatibility is maintained."
        ])
        guidelines_list.extend([
            "Zero functional changes allowed.",
            "Do not add new dependencies.",
            "Ensure clippy/linter produces zero warnings on changed code."
        ])
        out_of_scope_list.extend([
            "Adding new features",
            "Modifying existing public API signatures"
        ])
    elif journey == "cleanup":
        acceptance_criteria.extend([
            "Unused code, assets, or dependencies are removed.",
            "Documentation or formatting is cleaned up.",
            "Existing tests still pass."
        ])
        guidelines_list.extend([
            "Do not modify active production code logic.",
            "Only delete dead code that is verified to have no callers."
        ])
        destructive_change_policy = {"allowed": True, "requiresHumanApproval": True, "allowPatterns": ["**"]}
        out_of_scope_list.extend([
            "Modifying business logic",
            "Adding new features"
        ])

    contract = {
        "contractVersion": 2,
        "workItemId": task,
        "mode": args.mode,
        "title": title,
        "baseCommit": base_commit,
        "baselineDirtyPaths": baseline_dirty_paths,
        "scope": [contract_rel, summary_rel, ".ai/work-items/archive/**"],
        "outOfScope": out_of_scope_list,
        "sources": [{"path": contract_rel, "reason": "Initial Work Item skeleton."}],
        "unknowns": ["Replace this with concrete open questions, or clear it before mode code."],
        "notCodable": False,
        "riskAssessment": {
            "level": "medium",
            "riskTypes": ["scope_unclear"],
            "reason": "Initial skeleton; replace with task-specific implementation and review risks.",
        },
        "agentCapability": {
            "canImplement": False,
            "canVerify": False,
            "needsHumanDecision": True,
            "blockedReason": "Initial skeleton; clear unknowns and confirm verification before coding.",
        },
        "executionDecision": {
            "status": "needs_human_decision",
            "reason": "Initial skeleton must be completed before execution.",
        },
        "preReviewWarnings": [
            "Replace with task-specific review focus, or clear when no special review focus remains."
        ],
        "checkpointPolicy": {
            "requiredBeforeFinish": True,
            "requiredStages": list(DEFAULT_CHECKPOINT_STAGES),
            "reason": "Record at least one checkpoint before finishing to reduce mid-task drift.",
        },
        "acceptance": acceptance_criteria,
        "guidelines": guidelines_list,
        "verification": default_verification(),
        "destructiveChangePolicy": destructive_change_policy,
        "restrictedWriteApproval": {
            "approved": False,
            "approvedBy": "",
            "reason": "Set only when a human explicitly approves restricted governance paths.",
        },
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
        "verification": [{"check": item["check"], "result": "not_run"} for item in contract["verification"]],
        "guidelinesCompliance": [{"guideline": item, "compliant": False, "evidence": "Not verified."} for item in guidelines_list],
        "unknownsRemaining": ["Replace this before finishing the Work Item."],
        "risk": {"level": "medium", "detail": "Initial skeleton; scope and acceptance still need task-specific review."},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
        "residualRisks": [
            {
                "level": "medium",
                "area": "scope",
                "detail": "Initial skeleton; replace with actual residual risks before finishing.",
                "reviewRecommended": True,
                "followUpCandidate": False,
            }
        ],
        "reviewReadiness": {
            "status": "not_ready",
            "reason": "Initial skeleton; required checks have not run.",
            "expectedReviewFocus": [],
        },
        "boundaryChecks": {
            "runtimeEntrypoints": "not_applicable",
            "userVisibleOutput": "not_applicable",
            "persistence": "not_applicable",
            "localization": "not_applicable",
            "generatedArtifacts": "not_applicable",
            "makeEntrypoints": "not_applicable",
        },
        "userCorrectionsCaptured": [],
        "userCorrectionSolidification": [],
        "checkpointEvidence": [],
        "knownGaps": ["Replace this before finishing the Work Item."],
        "overclaimPrevention": "Do not report completion for checks or behavior that were not verified.",
    }
    status_path = PROJECT_ROOT / ".ai" / "cockpit" / "current_status.md"
    previous_status = status_path.read_bytes() if status_path.exists() else None
    save_json(contract_path, contract)
    save_json(summary_path, summary)
    try:
        write_active_status(contract_path, summary_path)
    except (OSError, RuntimeError, ValueError) as exc:
        contract_path.unlink(missing_ok=True)
        summary_path.unlink(missing_ok=True)
        if previous_status is None:
            status_path.unlink(missing_ok=True)
        else:
            status_path.parent.mkdir(parents=True, exist_ok=True)
            status_path.write_bytes(previous_status)
        print(f"ERROR: failed to generate Cockpit status; Work Item creation rolled back: {exc}", file=sys.stderr)
        return 1
    print(f"Work Item skeleton created: {task}")
    print(f"contract: {contract_rel}")
    print(f"summary: {summary_rel}")

    create_observability(work_item_id=task).work_item_started(fields={"mode": args.mode, "title": title})
    return 0


if __name__ == "__main__":
    sys.exit(main())
