#!/usr/bin/env python3
"""Validate active Work Item files and cockpit status agree."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from ai_common import PROJECT_ROOT


ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"
DEFAULT_STATUS = PROJECT_ROOT / ".ai" / "cockpit" / "current_status.md"


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def active_contracts() -> list[Path]:
    if not ACTIVE_DIR.exists():
        return []
    return sorted(ACTIVE_DIR.glob("*.contract.json"))


def active_summaries() -> list[Path]:
    if not ACTIVE_DIR.exists():
        return []
    return sorted(ACTIVE_DIR.glob("*.summary.json"))


def status_text(status_path: Path) -> str:
    if not status_path.exists():
        return ""
    return status_path.read_text(encoding="utf-8")


def no_active_changed_files(text: str) -> list[str]:
    try:
        block = text.split("## Changed Files", 1)[1].split("\n## ", 1)[0]
    except IndexError:
        return []
    return sorted(
        match.group(1) for line in block.splitlines() if (match := re.match(r"^- `([^`]+)`$", line))
    )


def no_active_worktree_count(text: str) -> int | None:
    match = re.search(r"- Worktree Change Count: `(\d+)`", text)
    return int(match.group(1)) if match else None


def git_records(text: str) -> list[str]:
    if "\0" in text:
        return [item for item in text.split("\0") if item]
    return [line for line in text.splitlines() if line]


def live_no_active_changed_files(status_path: Path) -> list[str]:
    try:
        relative_status = relative(status_path)
    except ValueError:
        relative_status = status_path.as_posix()
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if head.returncode != 0:
        return []
    changed: set[str] = set()
    diff = subprocess.run(
        ["git", "diff", "--name-only", "-z", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if diff.returncode == 0:
        changed.update(
            line.strip() for line in git_records(getattr(diff, "stdout", "")) if line.strip()
        )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if untracked.returncode == 0:
        changed.update(
            line.strip() for line in git_records(getattr(untracked, "stdout", "")) if line.strip()
        )
    changed.discard(relative_status)
    return sorted(changed)


def validate_status_consistency(status_path: Path = DEFAULT_STATUS) -> list[str]:
    issues: list[str] = []
    contracts = active_contracts()
    summaries = active_summaries()
    contract_ids = {path.name.removesuffix(".contract.json") for path in contracts}
    summary_ids = {path.name.removesuffix(".summary.json") for path in summaries}
    text = status_text(status_path)

    if contract_ids != summary_ids:
        for item in sorted(contract_ids - summary_ids):
            issues.append(
                f"active Contract has no matching Summary: {item}; create the missing Summary or archive/remove the Contract"
            )
        for item in sorted(summary_ids - contract_ids):
            issues.append(
                f"active Summary has no matching Contract: {item}; create the missing Contract or archive/remove the Summary"
            )

    if len(contract_ids) > 1:
        issues.append(
            f"multiple active Work Items found: {', '.join(sorted(contract_ids))}; keep only one active Work Item"
        )

    if not text:
        issues.append(f"cockpit status is missing: {relative(status_path)}")
        return issues

    if not contract_ids and not summary_ids:
        if "- State: `no_active_work_item`" not in text:
            issues.append(
                "cockpit status is not no_active_work_item while no active Work Item exists; run `make repair-ai-status`"
            )
        recorded = no_active_worktree_count(text)
        live = len(live_no_active_changed_files(status_path))
        if (
            no_active_changed_files(text)
            or (recorded is None and live > 0)
            or (recorded is not None and live != recorded)
        ):
            issues.append(
                "cockpit status no-active state must not persist changed files; run `make repair-ai-status`"
            )
        return issues

    if len(contract_ids) == 1 and len(summary_ids) == 1 and contract_ids == summary_ids:
        task = next(iter(contract_ids))
        contract_path = relative(ACTIVE_DIR / f"{task}.contract.json")
        summary_path = relative(ACTIVE_DIR / f"{task}.summary.json")
        if "- State: `no_active_work_item`" in text:
            issues.append(
                "cockpit status is no_active_work_item while an active Work Item exists; run `make repair-ai-status`"
            )
        if f"- Task: `{task}`" not in text:
            issues.append(
                f"cockpit status Task does not match active Work Item: {task}; run `make repair-ai-status`"
            )
        if f"- Contract Path: `{contract_path}`" not in text:
            issues.append(
                f"cockpit status Contract Path does not match active Contract: {contract_path}; run `make repair-ai-status`"
            )
        if f"- Summary Path: `{summary_path}`" not in text:
            issues.append(
                f"cockpit status Summary Path does not match active Summary: {summary_path}; run `make repair-ai-status`"
            )

    return issues


def repair_status(status_path: Path = DEFAULT_STATUS) -> int:
    contracts = active_contracts()
    summaries = active_summaries()
    contract_ids = {path.name.removesuffix(".contract.json") for path in contracts}
    summary_ids = {path.name.removesuffix(".summary.json") for path in summaries}

    if contract_ids != summary_ids or len(contract_ids) > 1:
        for issue in validate_status_consistency(status_path):
            print(f"[ERROR] cannot auto-repair: {issue}", file=sys.stderr)
        return 1

    command = [sys.executable, "scripts/ai_generate_status.py"]
    if not contract_ids:
        command.append("--no-active")
    else:
        task = next(iter(contract_ids))
        command.extend(
            [
                relative(ACTIVE_DIR / f"{task}.contract.json"),
                "--summary",
                relative(ACTIVE_DIR / f"{task}.summary.json"),
            ]
        )
    if status_path != DEFAULT_STATUS:
        command.extend(["--output", str(status_path)])
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        return result.returncode

    issues = validate_status_consistency(status_path)
    if issues:
        for issue in issues:
            print(f"[ERROR] repair did not produce consistent status: {issue}", file=sys.stderr)
        return 1
    print("ai status repaired")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate AI Cockpit active/status consistency.")
    parser.add_argument("--status", default=str(DEFAULT_STATUS), help="Path to current_status.md.")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Regenerate current_status.md when the active state is repairable.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repair:
        return repair_status(Path(args.status))
    issues = validate_status_consistency(Path(args.status))
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print("ai status consistency check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
