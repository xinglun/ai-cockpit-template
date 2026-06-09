#!/usr/bin/env python3
"""Run finish checks for a Work Item through the Makefile."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from ai_common import PROJECT_ROOT
from ai_observability import create_observability, elapsed_ms


ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"


def task_paths(task: str) -> tuple[str, str]:
    contract = ACTIVE_DIR / f"{task}.contract.json"
    summary = ACTIVE_DIR / f"{task}.summary.json"
    return contract.relative_to(PROJECT_ROOT).as_posix(), summary.relative_to(PROJECT_ROOT).as_posix()


def run(command: list[str]) -> tuple[int, int]:
    print("$ " + " ".join(command))
    start = time.time()
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    return result.returncode, elapsed_ms(start)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AI Work Item finish checks.")
    parser.add_argument("--task", required=True)
    parser.add_argument("--skip-quality", action="store_true", help="Skip the project quality gate.")
    parser.add_argument("--archive", action=argparse.BooleanOptionalAction, default=True, help="Archive Work Item after successful checks.")
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

    obs = create_observability(work_item_id=args.task)
    total_start = time.time()
    commands = [
        ["make", "check-ai-contract", f"CONTRACT={contract}"],
        ["make", "check-ai-scope", f"CONTRACT={contract}"],
        ["make", "check-ai-guards"],
        ["make", "check-ai-backtrack"],
        ["make", "check-ai-coverage-guard"],
        ["make", "check-ai-change-summary", f"SUMMARY={summary}", f"CONTRACT={contract}"],
        ["make", "generate-cockpit-status", f"CONTRACT={contract}", f"SUMMARY={summary}"],
        ["make", "check-ai-status", f"CONTRACT={contract}", f"SUMMARY={summary}"],
        ["make", "check-ai-status-consistency"],
    ]
    if not args.skip_quality:
        commands.append(["make", "quality"])

    for command in commands:
        cmd_str = " ".join(command)
        check_id = command[1] if len(command) > 1 else cmd_str
        obs.check_started(check_id=check_id, command=cmd_str)
        code, duration = run(command)
        if code != 0:
            obs.check_failed(check_id=check_id, command=cmd_str, duration_ms=duration)
            obs.work_item_finished(result="failed", duration_ms=elapsed_ms(total_start))
            return code
        obs.check_passed(check_id=check_id, command=cmd_str, duration_ms=duration)

    print("Work Item finish checks passed")
    if args.archive:
        archive_command = ["make", "archive-work-item", f"CONTRACT={contract}"]
        cmd_str = " ".join(archive_command)
        obs.check_started(check_id="archive-work-item", command=cmd_str)
        code, duration = run(archive_command)
        if code != 0:
            obs.check_failed(check_id="archive-work-item", command=cmd_str, duration_ms=duration)
            obs.work_item_finished(result="failed", duration_ms=elapsed_ms(total_start))
            return code
        obs.check_passed(check_id="archive-work-item", command=cmd_str, duration_ms=duration)
    obs.work_item_finished(result="passed", duration_ms=elapsed_ms(total_start))
    return 0


if __name__ == "__main__":
    sys.exit(main())
