#!/usr/bin/env python3
"""Report production changes that do not include test changes."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
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


def association_rules(policy: dict[str, list[str]]) -> list[tuple[list[str], list[str]]]:
    rules = []
    for key, production_patterns in policy.items():
        if not key.startswith("associations.") or not key.endswith(".production"):
            continue
        prefix = key.removesuffix(".production")
        test_patterns = policy.get(f"{prefix}.tests", [])
        if production_patterns and test_patterns:
            rules.append((production_patterns, test_patterns))
    return rules


def expand_test_pattern(pattern: str, production_path: str) -> str:
    path = PurePosixPath(production_path)
    stem = path.stem
    module = stem
    for prefix in ("ai_check_", "ai_", "check_"):
        if module.startswith(prefix):
            module = module.removeprefix(prefix)
            break
    directory = "" if str(path.parent) == "." else path.parent.as_posix()
    return pattern.format(stem=stem, module=module, name=path.name, dir=directory)


def associated_test_exists(
    production_path: str,
    test_changes: list[str],
    rules: list[tuple[list[str], list[str]]],
) -> tuple[bool, bool]:
    matching_rules = [tests for production, tests in rules if included(production_path, production)]
    if not matching_rules:
        return False, False
    for test_patterns in matching_rules:
        expanded = [expand_test_pattern(pattern, production_path) for pattern in test_patterns]
        if any(included(test_path, expanded) for test_path in test_changes):
            return True, True
    return True, False


def detect(paths: list[str]) -> list[CoverageGuardItem]:
    policy = simple_yaml_lists(POLICY)
    prod_include = policy.get("production.include", ["src/**", "lib/**"])
    prod_exclude = policy.get(
        "production.exclude", ["tests/**", "test/**", "**/*test*", "**/*spec*"]
    )
    test_include = policy.get("tests.include", ["tests/**", "test/**", "**/*test*", "**/*spec*"])

    production_changes = [
        path for path in paths if included(path, prod_include) and not included(path, prod_exclude)
    ]
    test_changes = [path for path in paths if included(path, test_include)]
    if not production_changes:
        return []
    items = []
    rules = association_rules(policy)
    for path in production_changes:
        configured, matched = associated_test_exists(path, test_changes, rules)
        if matched:
            continue
        detail = (
            "Production code changed, but no associations.*.production rule covers this path."
            if not configured
            else "Production code changed, but the diff has no test path matched by its configured association."
        )
        items.append(
            CoverageGuardItem(
                "warning",
                "missing_test_diff_for_production_change",
                path,
                detail,
            )
        )
    return items


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
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    obs = create_observability()
    duration = elapsed_ms(start)
    if items:
        mode = "report-only warnings" if report_only else "blocking findings"
        print(f"coverage guard {mode}: {len(items)}")
        for item in items:
            print(f"[{item.severity}] {item.kind}: {item.path} - {item.detail}")
            obs.guard_violation(
                check_id="aiCoverageGuard",
                severity=item.severity,
                path=item.path,
                detail=f"{item.kind}: {item.detail}",
            )
    else:
        print("coverage guard: no issues")
    print(f"report: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    if items and not report_only:
        obs.check_failed(
            check_id="aiCoverageGuard",
            duration_ms=duration,
            detail="production changes lack test changes",
        )
        return 1
    obs.check_passed(
        check_id="aiCoverageGuard", duration_ms=duration, fields={"warnings": len(items)}
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
