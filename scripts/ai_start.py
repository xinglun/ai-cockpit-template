#!/usr/bin/env python3
"""Create a new Work Item Contract and Summary skeleton."""

from __future__ import annotations

import contextlib
import argparse
import hashlib
import fcntl
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator
from ai_common import (
    PROJECT_ROOT,
    capture_dirty_baseline,
    clean_git_environment,
    current_head,
    save_json,
)
from ai_check_status_consistency import DEFAULT_STATUS, validate_status_consistency
from ai_check_diff_ownership import format_preview, preview
from ai_generate_status import write_active_status, write_no_active_status
from ai_observability import create_observability


ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"
START_LOCK_FILENAME = ".ai-start.lock"
MODES = ["investigate", "author_todo", "code", "review", "cleanup"]
JOURNEYS = ["feature", "bugfix", "refactor", "cleanup"]
DEFAULT_CHECKPOINT_STAGES = ["before_edit", "before_finish"]
DEFAULT_VERIFICATION_CHECKS = [
    "aiWorkItem",
    "aiScope",
    "aiGuards",
    "aiCheckpoint",
    "aiAgentRisk",
    "aiReviewPolicy",
    "aiBacktrack",
    "aiCoverage",
    "aiScenarioCoverage",
    "aiGuidelines",
    "aiSummary",
    "aiStatus",
    "aiStatusCheck",
    "aiStatusConsistency",
    "aiDiffOwnership",
    "quality",
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
    parser.add_argument(
        "--journey", default="feature", choices=JOURNEYS, help="Work journey preset."
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing skeleton.")
    return parser.parse_args()


def refresh_stale_no_active_status(issues: list[str]) -> list[str]:
    stale_messages = {
        "cockpit status Changed Files do not match current Git changes; run `make repair-ai-status`",
        "cockpit status no-active state must not persist changed files; run `make repair-ai-status`",
    }
    if len(issues) == 1 and issues[0] in stale_messages:
        write_no_active_status(DEFAULT_STATUS)
        return validate_status_consistency()
    return issues


def active_work_item_paths() -> list[Path]:
    if not ACTIVE_DIR.exists():
        return []
    return sorted(path for path in ACTIVE_DIR.glob("*.json") if path.is_file())


def start_lock_path() -> Path:
    repo_hash = hashlib.sha256(str(PROJECT_ROOT.resolve()).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"codex-ai-start-{repo_hash}{START_LOCK_FILENAME}"


@contextlib.contextmanager
def acquire_start_lock() -> Iterator[None]:
    lock_path = start_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(
                "another ai-start is already in progress; wait for it to finish before creating a new Work Item"
            ) from exc
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(f"pid={os.getpid()}\n")
        lock_file.flush()
        try:
            yield
        finally:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            lock_path.unlink(missing_ok=True)


def run_make(target: str, *, contract: str | None = None) -> tuple[int, str]:
    command = ["make", target]
    if contract:
        command.append(f"CONTRACT={contract}")
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=clean_git_environment(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return 127, str(exc)
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def journey_policy(
    journey: str,
) -> tuple[list[str], list[str], list[str], dict[str, object]]:
    """Return acceptance, guidelines, exclusions, and destructive policy for a journey."""
    acceptance = ["The Work Item Contract is updated for the actual task."]
    guidelines: list[str] = []
    out_of_scope: list[str] = []
    destructive_policy: dict[str, object] = {
        "allowed": False,
        "requiresHumanApproval": True,
        "allowPatterns": [],
    }
    if journey == "feature":
        acceptance.extend(
            [
                "The new feature is implemented according to requirements.",
                "Unit tests are added to verify the new feature.",
                "User documentation or comments are updated.",
            ]
        )
        guidelines.extend(
            [
                "New public APIs must be documented.",
                "Do not import internal modules from other features.",
            ]
        )
    elif journey == "bugfix":
        acceptance.extend(
            [
                "The bug is reproduced by a test case.",
                "The fix resolves the bug and the test passes.",
                "No regression is introduced in existing functionality.",
            ]
        )
        guidelines.extend(
            [
                "Fix must target the root cause, not just the symptom.",
                "Avoid side effects on other components.",
            ]
        )
    elif journey == "refactor":
        acceptance.extend(
            [
                "Code structural changes are completed without changing functional behavior.",
                "All existing unit tests pass without modifications.",
                "API backwards compatibility is maintained.",
            ]
        )
        guidelines.extend(
            [
                "Zero functional changes allowed.",
                "Do not add new dependencies.",
                "Ensure clippy/linter produces zero warnings on changed code.",
            ]
        )
        out_of_scope.extend(["Adding new features", "Modifying existing public API signatures"])
    elif journey == "cleanup":
        acceptance.extend(
            [
                "Unused code, assets, or dependencies are removed.",
                "Documentation or formatting is cleaned up.",
                "Existing tests still pass.",
            ]
        )
        guidelines.extend(
            [
                "Do not modify active production code logic.",
                "Only delete dead code that is verified to have no callers.",
            ]
        )
        out_of_scope.extend(["Modifying business logic", "Adding new features"])
    return acceptance, guidelines, out_of_scope, destructive_policy


def persist_work_item(
    contract_path: Path,
    summary_path: Path,
    contract: dict[str, object],
    summary: dict[str, object],
) -> bool:
    """Persist a new Work Item and roll back if active status generation fails."""
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
        print(
            f"ERROR: failed to generate Cockpit status; Work Item creation rolled back: {exc}",
            file=sys.stderr,
        )
        return False
    return True


def run_code_preflight(contract_path: Path, summary_path: Path, contract_rel: str) -> int:
    """Run code-mode preflight and refresh status with its result."""
    code, output = run_make("ai-preflight", contract=contract_rel)
    if output.strip():
        print(output.rstrip())
    try:
        write_active_status(contract_path, summary_path, announce=False)
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            f"ERROR: failed to refresh Cockpit status after Preflight Review: {exc}",
            file=sys.stderr,
        )
        return 1
    return code


def validate_start_state(task: str, *, force: bool) -> tuple[Path, Path, str] | None:
    """Validate lifecycle state and return target paths plus trusted base commit."""
    consistency_issues = refresh_stale_no_active_status(validate_status_consistency())
    if consistency_issues:
        for issue in consistency_issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        print(
            "ERROR: fix Work Item lifecycle/status consistency before creating a new Work Item. "
            "Run `make repair-ai-status` when the active files are paired; otherwise clean up active Work Item files manually.",
            file=sys.stderr,
        )
        return None

    active_paths = active_work_item_paths()
    if active_paths:
        active_items = ", ".join(path.stem for path in active_paths)
        print(
            "ERROR: an active Work Item already exists: "
            f"{active_items}. Finish or archive it before creating a new Work Item.",
            file=sys.stderr,
        )
        return None

    contract_path = ACTIVE_DIR / f"{task}.contract.json"
    summary_path = ACTIVE_DIR / f"{task}.summary.json"
    if not force and (contract_path.exists() or summary_path.exists()):
        print(f"ERROR: Work Item already exists: {task}", file=sys.stderr)
        return None

    base_commit = current_head()
    if not base_commit:
        print(
            "ERROR: ai-start requires an initial Git commit so baseCommit is trustworthy.",
            file=sys.stderr,
        )
        return None
    return contract_path, summary_path, base_commit


def main() -> int:
    args = parse_args()
    try:
        task = slug(args.task)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        lock_context: contextlib.AbstractContextManager[None] = acquire_start_lock()
        lock_context.__enter__()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        start_state = validate_start_state(task, force=args.force)
        if start_state is None:
            return 1
        contract_path, summary_path, base_commit = start_state
        title = args.title or task.replace("_", " ")
        baseline_dirty_paths = capture_dirty_baseline()
        contract_rel = contract_path.relative_to(PROJECT_ROOT).as_posix()
        summary_rel = summary_path.relative_to(PROJECT_ROOT).as_posix()

        acceptance_criteria, guidelines_list, out_of_scope_list, destructive_change_policy = (
            journey_policy(args.journey)
        )

        contract = {
            "contractVersion": 2,
            "workItemId": task,
            "mode": args.mode,
            "title": title,
            "baseCommit": base_commit,
            "baselineDirtyPaths": baseline_dirty_paths,
            "scope": [
                contract_rel,
                summary_rel,
                ".ai/cockpit/current_status.md",
                ".ai/work-items/archive/**",
            ],
            "outOfScope": out_of_scope_list,
            "sources": [{"path": contract_rel, "reason": "Initial Work Item skeleton."}],
            "unknowns": [
                "Replace this with concrete open questions, or clear it before mode code."
            ],
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
            # intent セクション（V2 以降）: AI が「なぜこの変更が存在するか」を理解するための文脈。
            # 全フィールドは任意。None は「未記入」を意味し、バリデーターに空文字列エラーを起こさない。
            # 現在の AI ワークフローで最も自然に記入されるのは problem / constraints / rationale の 3 フィールド。
            # businessGoal / userGoal / nonGoals はセクションに存在するが、文脈が提供されない限り記入しない。
            "intent": {
                "problem": None,
                "constraints": [],
                "rationale": None,
            },
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
            "summaryVersion": 2,
            "workItemId": task,
            "contractPath": contract_rel,
            "changedFiles": [
                {"path": contract_rel, "reason": "Created the Work Item Contract skeleton."},
                {"path": summary_rel, "reason": "Created the AI Change Summary skeleton."},
            ],
            "sourcesUsed": [contract_rel],
            "verification": [
                {"check": item["check"], "result": "not_run"} for item in contract["verification"]
            ],
            "guidelinesCompliance": [
                {"guideline": item, "compliant": False, "evidence": "Not verified."}
                for item in guidelines_list
            ],
            "unknownsRemaining": ["Replace this before finishing the Work Item."],
            "risk": {
                "level": "medium",
                "detail": "Initial skeleton; scope and acceptance still need task-specific review.",
            },
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
        if not persist_work_item(contract_path, summary_path, contract, summary):
            return 1
        create_observability(work_item_id=task).work_item_started(
            fields={"mode": args.mode, "title": title}
        )

        # This deliberately uses the complete local diff, not the Contract-aware
        # task delta: files dirty before ai-start are not adopted by the new task.
        print("\n".join(format_preview(preview())))

        if args.mode == "code":
            code = run_code_preflight(contract_path, summary_path, contract_rel)
            if code != 0:
                return code

        print(f"Work Item skeleton created: {task}")
        print(f"contract: {contract_rel}")
        print(f"summary: {summary_rel}")
        return 0
    finally:
        lock_context.__exit__(None, None, None)


if __name__ == "__main__":
    sys.exit(main())
