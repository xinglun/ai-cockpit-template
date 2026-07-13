#!/usr/bin/env python3
"""Report undeclared backtracking in the current diff."""

from __future__ import annotations

import json
import sys
import time
import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from ai_common import PROJECT_ROOT, changed_name_status, included, simple_yaml_scalars
from ai_observability import create_observability, elapsed_ms


REPORT_PATH = PROJECT_ROOT / "target" / "ai_backtrack_report.json"
POLICY_PATH = PROJECT_ROOT / ".ai" / "guards" / "backtrack_policy.yaml"


@dataclass(frozen=True)
class BacktrackItem:
    severity: str
    kind: str
    path: str
    detail: str


def is_test_path(path: str) -> bool:
    return included(path, ["tests/**", "test/**", "**/*test*", "**/*spec*"])


def detect_items(changes: list[tuple[str, str]]) -> list[BacktrackItem]:
    items: list[BacktrackItem] = []
    for status, path in changes:
        if status.startswith("D") and is_test_path(path):
            items.append(
                BacktrackItem(
                    "warning",
                    "deleted_test",
                    path,
                    "A test file or test-like path was deleted. Record the reason in destructiveChanges if intentional.",
                )
            )
        if status.startswith("D") and included(
            path, ["**/snapshots/**", "**/*.snap", "**/*.snapshot"]
        ):
            items.append(
                BacktrackItem(
                    "warning",
                    "deleted_snapshot",
                    path,
                    "A snapshot was deleted. Confirm this is not an output contract regression.",
                )
            )
        if status.startswith("D") and included(path, [".ai/work-items/**"]):
            items.append(
                BacktrackItem(
                    "warning",
                    "removed_work_item_record",
                    path,
                    "A Work Item record was deleted. Record cleanup intent in the Summary.",
                )
            )
    return items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report backtrack guard policy outcomes.")
    parser.add_argument("--verbose", action="store_true", help="Print detailed evaluations.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.time()
    try:
        changes = changed_name_status()
        if args.verbose:
            print(f"[DEBUG] backtrack guard: scanning {len(changes)} changed path(s)")
            for status, path in changes:
                print(f"[DEBUG]   evaluating: '{path}' (status: {status})")
        items = detect_items(changes)
    except RuntimeError as exc:
        print(f"backtrack guard failed: {exc}", file=sys.stderr)
        return 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_only = simple_yaml_scalars(POLICY_PATH).get("reportOnly", "true").lower() == "true"
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "warning" if items else "none",
        "reportOnly": report_only,
        "items": [asdict(item) for item in items],
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    obs = create_observability()
    duration = elapsed_ms(start)
    if items:
        mode = "report-only warnings" if report_only else "blocking findings"
        print(f"backtrack guard {mode}: {len(items)}")
        for item in items:
            print(f"[{item.severity}] {item.kind}: {item.path} - {item.detail}")
            obs.guard_violation(
                check_id="aiBacktrack",
                severity=item.severity,
                path=item.path,
                detail=f"{item.kind}: {item.detail}",
            )
    else:
        print("backtrack guard: no issues")
    print(f"report: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    if items and not report_only:
        obs.check_failed(
            check_id="aiBacktrack", duration_ms=duration, detail="protected evidence removal"
        )
        return 1
    obs.check_passed(check_id="aiBacktrack", duration_ms=duration, fields={"warnings": len(items)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
