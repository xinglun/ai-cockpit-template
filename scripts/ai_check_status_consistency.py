#!/usr/bin/env python3
"""Validate active Work Item files and cockpit status agree."""

from __future__ import annotations

import argparse
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


def validate_status_consistency(status_path: Path = DEFAULT_STATUS) -> list[str]:
    issues: list[str] = []
    contracts = active_contracts()
    summaries = active_summaries()
    contract_ids = {path.name.removesuffix(".contract.json") for path in contracts}
    summary_ids = {path.name.removesuffix(".summary.json") for path in summaries}
    text = status_text(status_path)

    if contract_ids != summary_ids:
        for item in sorted(contract_ids - summary_ids):
            issues.append(f"active Contract has no matching Summary: {item}")
        for item in sorted(summary_ids - contract_ids):
            issues.append(f"active Summary has no matching Contract: {item}")

    if len(contract_ids) > 1:
        issues.append(f"multiple active Work Items found: {', '.join(sorted(contract_ids))}")

    if not text:
        issues.append(f"cockpit status is missing: {relative(status_path)}")
        return issues

    if not contract_ids and not summary_ids:
        if "- State: `no_active_work_item`" not in text:
            issues.append("cockpit status is not no_active_work_item while no active Work Item exists")
        return issues

    if len(contract_ids) == 1 and len(summary_ids) == 1 and contract_ids == summary_ids:
        task = next(iter(contract_ids))
        contract_path = relative(ACTIVE_DIR / f"{task}.contract.json")
        summary_path = relative(ACTIVE_DIR / f"{task}.summary.json")
        if "- State: `no_active_work_item`" in text:
            issues.append("cockpit status is no_active_work_item while an active Work Item exists")
        if f"- Task: `{task}`" not in text:
            issues.append(f"cockpit status Task does not match active Work Item: {task}")
        if f"- Contract Path: `{contract_path}`" not in text:
            issues.append(f"cockpit status Contract Path does not match active Contract: {contract_path}")
        if f"- Summary Path: `{summary_path}`" not in text:
            issues.append(f"cockpit status Summary Path does not match active Summary: {summary_path}")

    return issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate AI Cockpit active/status consistency.")
    parser.add_argument("--status", default=str(DEFAULT_STATUS), help="Path to current_status.md.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    issues = validate_status_consistency(Path(args.status))
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print("ai status consistency check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
