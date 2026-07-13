#!/usr/bin/env python3
"""Run finish checks for a Work Item through the Makefile."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_common import (
    PROJECT_ROOT,
    changed_paths,
    clean_git_environment,
    current_head,
    load_json,
    path_fingerprint,
    redact_machine_paths,
    redact_sensitive_output,
    render_check_command,
    save_json,
    verification_key,
)
from ai_check_diff_ownership import format_preview, preview
from ai_observability import create_observability, elapsed_ms


ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"


def task_paths(task: str) -> tuple[str, str]:
    contract = ACTIVE_DIR / f"{task}.contract.json"
    summary = ACTIVE_DIR / f"{task}.summary.json"
    return contract.relative_to(PROJECT_ROOT).as_posix(), summary.relative_to(
        PROJECT_ROOT
    ).as_posix()


def run(command: list[str]) -> tuple[int, int, str]:
    print("$ " + " ".join(command))
    start = time.time()
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=clean_git_environment(),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return result.returncode, elapsed_ms(start), result.stdout or ""


def evidence(
    check_id: str,
    command: str,
    code: int,
    duration: int,
    output: str,
    *,
    contract_hash: str,
    commit_sha: str,
    execution_contract_path: str,
    execution_summary_path: str,
    worktree_digest: str,
) -> dict[str, Any]:
    compact = redact_sensitive_output(output)
    compact = redact_machine_paths(compact)
    compact = " ".join(compact.split())[:500]
    return {
        "check": check_id,
        "command": command,
        "result": "passed" if code == 0 else "failed",
        "runner": "ai_finish",
        "executedAt": datetime.now(timezone.utc).isoformat(),
        "exitCode": code,
        "durationMs": duration,
        "outputDigest": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "commandHash": hashlib.sha256(" ".join(command.split()).encode("utf-8")).hexdigest(),
        "contractHash": contract_hash,
        "commitSha": commit_sha,
        "executionContractPath": execution_contract_path,
        "executionSummaryPath": execution_summary_path,
        "worktreeDigest": worktree_digest,
        "outputSummary": compact,
    }


def pending_evidence(
    check_id: str,
    command: str,
    *,
    contract_hash: str,
    commit_sha: str,
    execution_contract_path: str,
    execution_summary_path: str,
    worktree_digest: str,
) -> dict[str, Any]:
    item = evidence(
        check_id,
        command,
        0,
        0,
        "pending transactional validation",
        contract_hash=contract_hash,
        commit_sha=commit_sha,
        execution_contract_path=execution_contract_path,
        execution_summary_path=execution_summary_path,
        worktree_digest=worktree_digest,
    )
    item["runner"] = "ai_finish_pending"
    return item


def worktree_digest(paths: list[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path_fingerprint(path).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def record_result(summary_path: Path, item: dict[str, Any]) -> None:
    if not summary_path.exists():
        raise FileNotFoundError(f"summary not found: {summary_path.relative_to(PROJECT_ROOT)}")
    summary = load_json(summary_path)
    values = summary.get("verification", [])
    if not isinstance(values, list):
        values = []
    summary["verification"] = [
        entry
        for entry in values
        if not (isinstance(entry, dict) and verification_key(entry) == verification_key(item))
    ] + [item]
    save_json(summary_path, summary)


def verification_priority(item: dict[str, Any]) -> int:
    check_id = verification_key(item)
    if check_id == "aiStatus":
        return 20
    if check_id == "aiStatusCheck":
        return 30
    if check_id == "aiStatusConsistency":
        return 40
    if check_id == "aiAgentRisk":
        return 50
    if check_id == "aiSummary":
        return 51
    return 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AI Work Item finish checks.")
    parser.add_argument("--task", required=True)
    parser.add_argument(
        "--skip-quality", action="store_true", help="Skip the project quality gate."
    )
    parser.add_argument(
        "--archive",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Archive Work Item after successful checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract, summary = task_paths(args.task)
    if not (PROJECT_ROOT / contract).exists():
        print(f"ERROR: Contract does not exist: {contract}", file=sys.stderr)
        return 1
    if not (PROJECT_ROOT / summary).exists():
        print(f"ERROR: Summary does not exist: {summary}", file=sys.stderr)
        return 1

    contract_path = PROJECT_ROOT / contract
    summary_path = PROJECT_ROOT / summary
    contract_data = load_json(contract_path)
    if contract_data.get("contractVersion") != 2:
        print(
            "ERROR: ai-finish executes only contractVersion 2 check-ID Contracts", file=sys.stderr
        )
        return 2
    contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    commit_sha = current_head()
    declared = contract_data.get("verification", [])
    if not isinstance(declared, list):
        print("ERROR: Contract verification must be a list", file=sys.stderr)
        return 1

    obs = create_observability(work_item_id=args.task)
    total_start = time.time()
    declared_items = [item for item in declared if isinstance(item, dict)]
    declared_items.sort(key=verification_priority)
    ownership = preview(contract=contract_data)
    print("\n".join(format_preview(ownership)))
    ownership_failures = [
        item for item in ownership if item.state not in {"active_owned", "archived_owned"}
    ]
    if ownership_failures:
        print(
            "ERROR: finish is blocked until every task-era changed path has Work Item ownership.",
            file=sys.stderr,
        )
        return 1
    transactional_markers_written = False
    for item in declared_items:
        if not isinstance(item, dict):
            continue
        check_id = verification_key(item)
        if not check_id or "command" in item:
            print(
                "ERROR: contractVersion 2 verification must use registered check IDs only",
                file=sys.stderr,
            )
            return 2
        if args.skip_quality and check_id == "quality":
            if item.get("required") is True:
                print(
                    "ERROR: --skip-quality cannot skip required Contract verification",
                    file=sys.stderr,
                )
                return 2
            continue
        try:
            cmd_str, command = render_check_command(
                check_id, contract_path=contract, summary_path=summary
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        obs.check_started(check_id=check_id, command=cmd_str)
        # Status, Agent Risk, and Summary form a self-referential lifecycle
        # cluster. Pending markers let status stabilize but are rejected by the
        # Summary checker if execution stops before actual evidence replaces them.
        if not transactional_markers_written and verification_priority(item) >= 20:
            current_worktree_digest = worktree_digest(changed_paths(contract_data))
            for candidate in declared_items:
                if verification_priority(candidate) >= 20:
                    candidate_id = verification_key(candidate)
                    candidate_command, _ = render_check_command(
                        candidate_id, contract_path=contract, summary_path=summary
                    )
                    record_result(
                        summary_path,
                        pending_evidence(
                            candidate_id,
                            candidate_command,
                            contract_hash=contract_hash,
                            commit_sha=commit_sha,
                            execution_contract_path=contract,
                            execution_summary_path=summary,
                            worktree_digest=current_worktree_digest,
                        ),
                    )
            transactional_markers_written = True
        # The Summary checker validates its own record. Replace only its pending
        # runner immediately before execution; failure overwrites it as failed.
        if check_id == "aiSummary":
            current_worktree_digest = worktree_digest(changed_paths(contract_data))
            record_result(
                summary_path,
                evidence(
                    check_id,
                    cmd_str,
                    0,
                    0,
                    "pending transactional validation",
                    contract_hash=contract_hash,
                    commit_sha=commit_sha,
                    execution_contract_path=contract,
                    execution_summary_path=summary,
                    worktree_digest=current_worktree_digest,
                ),
            )
        code, duration, output = run(command)
        current_worktree_digest = worktree_digest(changed_paths(contract_data))
        record_result(
            summary_path,
            evidence(
                check_id,
                cmd_str,
                code,
                duration,
                output,
                contract_hash=contract_hash,
                commit_sha=commit_sha,
                execution_contract_path=contract,
                execution_summary_path=summary,
                worktree_digest=current_worktree_digest,
            ),
        )
        if code != 0 and item.get("required") is True:
            obs.check_failed(check_id=check_id, command=cmd_str, duration_ms=duration)
            obs.work_item_finished(result="failed", duration_ms=elapsed_ms(total_start))
            return code
        if code == 0:
            obs.check_passed(check_id=check_id, command=cmd_str, duration_ms=duration)
        else:
            obs.check_failed(
                check_id=check_id,
                command=cmd_str,
                duration_ms=duration,
                detail="optional verification failed",
            )

    # Summary/status are self-referential artifacts. Stabilize them after all
    # declared result evidence has been written, then attest without mutating.
    stabilization = [
        (
            "aiStatus",
            ["make", "generate-cockpit-status", f"CONTRACT={contract}", f"SUMMARY={summary}"],
        ),
        (
            "aiStatusCheck",
            ["make", "check-ai-status", f"CONTRACT={contract}", f"SUMMARY={summary}"],
        ),
        ("aiStatusConsistency", ["make", "check-ai-status-consistency"]),
        (
            "aiAgentRisk",
            ["make", "check-ai-agent-risk", f"CONTRACT={contract}", f"SUMMARY={summary}"],
        ),
        (
            "aiSummary",
            ["make", "check-ai-change-summary", f"SUMMARY={summary}", f"CONTRACT={contract}"],
        ),
    ]
    for check_id, command in stabilization:
        obs.check_started(check_id=check_id, command=" ".join(command))
        code, duration, output = run(command)
        # Record actual result of stabilization check to Summary for debugging.
        current_worktree_digest = worktree_digest(changed_paths(contract_data))
        record_result(
            summary_path,
            evidence(
                check_id,
                " ".join(command),
                code,
                duration,
                output,
                contract_hash=contract_hash,
                commit_sha=commit_sha,
                execution_contract_path=contract,
                execution_summary_path=summary,
                worktree_digest=current_worktree_digest,
            ),
        )
        if code != 0:
            obs.check_failed(check_id=check_id, command=" ".join(command), duration_ms=duration)
            obs.work_item_finished(result="failed", duration_ms=elapsed_ms(total_start))
            return code
        obs.check_passed(check_id=check_id, command=" ".join(command), duration_ms=duration)

    print("Work Item finish checks passed")
    if args.archive:
        archive_command = ["make", "archive-work-item", f"CONTRACT={contract}"]
        cmd_str = " ".join(archive_command)
        obs.check_started(check_id="archive-work-item", command=cmd_str)
        code, duration, _ = run(archive_command)
        if code != 0:
            obs.check_failed(check_id="archive-work-item", command=cmd_str, duration_ms=duration)
            obs.work_item_finished(result="failed", duration_ms=elapsed_ms(total_start))
            return code
        obs.check_passed(check_id="archive-work-item", command=cmd_str, duration_ms=duration)
    obs.work_item_finished(result="passed", duration_ms=elapsed_ms(total_start))
    return 0


if __name__ == "__main__":
    sys.exit(main())
