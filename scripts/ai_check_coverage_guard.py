#!/usr/bin/env python3
"""Report production changes that do not include test changes."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from ai_common import PROJECT_ROOT, changed_paths, included, simple_yaml_lists, simple_yaml_scalars
from ai_observability import create_observability, elapsed_ms


POLICY = PROJECT_ROOT / ".ai" / "guards" / "coverage_policy.yaml"
REPORT_PATH = PROJECT_ROOT / "target" / "ai_coverage_guard_report.json"


@dataclass(frozen=True)
class CoverageGuardItem:
    severity: str
    kind: str
    path: str
    detail: str


def detect(paths: list[str]) -> list[CoverageGuardItem]:
    policy = simple_yaml_lists(POLICY)
    prod_include = policy.get("production.include", ["src/**", "lib/**"])
    prod_exclude = policy.get("production.exclude", ["tests/**", "test/**", "**/*test*", "**/*spec*"])
    test_include = policy.get("tests.include", ["tests/**", "test/**", "**/*test*", "**/*spec*"])

    production_changes = [path for path in paths if included(path, prod_include) and not included(path, prod_exclude)]
    test_changes = [path for path in paths if included(path, test_include)]
    if not production_changes or test_changes:
        return []
    return [
        CoverageGuardItem(
            "warning",
            "missing_test_diff_for_production_change",
            path,
            "Production code changed, but the same diff does not include a configured test path.",
        )
        for path in production_changes
    ]


def main() -> int:
    start = time.time()
    try:
        paths = changed_paths()
        items = detect(paths)
    except RuntimeError as exc:
        print(f"coverage guard failed: {exc}", file=sys.stderr)
        return 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_only = simple_yaml_scalars(POLICY).get("reportOnly", "true").lower() == "true"
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "warning" if items else "none",
        "reportOnly": report_only,
        "changedPaths": paths,
        "items": [asdict(item) for item in items],
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    obs = create_observability()
    duration = elapsed_ms(start)
    if items:
        mode = "report-only warnings" if report_only else "blocking findings"
        print(f"coverage guard {mode}: {len(items)}")
        for item in items:
            print(f"[{item.severity}] {item.kind}: {item.path} - {item.detail}")
            obs.guard_violation(check_id="aiCoverageGuard", severity=item.severity, path=item.path, detail=f"{item.kind}: {item.detail}")
    else:
        print("coverage guard: no issues")
    print(f"report: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    if items and not report_only:
        obs.check_failed(check_id="aiCoverageGuard", duration_ms=duration, detail="production changes lack test changes")
        return 1
    obs.check_passed(check_id="aiCoverageGuard", duration_ms=duration, fields={"warnings": len(items)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
