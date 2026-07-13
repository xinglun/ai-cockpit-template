#!/usr/bin/env python3
"""Validate file ownership and boundary guard manifests."""

from __future__ import annotations

import json
import argparse
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from ai_common import PROJECT_ROOT, changed_paths, first_match, load_json, parse_simple_manifest
from ai_observability import create_observability, elapsed_ms


OWNERSHIP = PROJECT_ROOT / ".ai" / "guards" / "file_ownership.yaml"
BOUNDARY = PROJECT_ROOT / ".ai" / "guards" / "file_boundary.yaml"
REPORT = PROJECT_ROOT / "target" / "ai_guard_report.json"
FORBIDDEN_WRITES = {"forbidden"}
FORBIDDEN_BOUNDARIES = {"runtime_artifact", "generated_local"}


@dataclass(frozen=True)
class GuardItem:
    severity: str
    kind: str
    path: str
    pattern: str
    detail: str


def detect(paths: list[str], *, restricted_approved: bool = False) -> list[GuardItem]:
    ownership = parse_simple_manifest(OWNERSHIP)
    boundary = parse_simple_manifest(BOUNDARY)
    items: list[GuardItem] = []
    for path in paths:
        owner_match = first_match(path, ownership)
        if owner_match:
            pattern, data = owner_match
            ai_write = data.get("aiWrite", "")
            if ai_write in FORBIDDEN_WRITES:
                items.append(
                    GuardItem("error", "forbidden_write", path, pattern, data.get("reason", ""))
                )
            elif ai_write == "restricted":
                severity = "warning" if restricted_approved else "error"
                items.append(
                    GuardItem(severity, "restricted_write", path, pattern, data.get("reason", ""))
                )
        boundary_match = first_match(path, boundary)
        if boundary_match:
            pattern, data = boundary_match
            if data.get("boundary", "") in FORBIDDEN_BOUNDARIES:
                items.append(
                    GuardItem("error", "forbidden_boundary", path, pattern, data.get("reason", ""))
                )
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ownership and boundary guards.")
    parser.add_argument("--contract")
    args = parser.parse_args()
    start = time.time()
    try:
        contract = load_json(Path(args.contract)) if args.contract else None
        approval = contract.get("restrictedWriteApproval") if isinstance(contract, dict) else None
        restricted_approved = isinstance(approval, dict) and approval.get("approved") is True
        paths = changed_paths(contract)
        items = detect(paths, restricted_approved=restricted_approved)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"guard check failed: {exc}", file=sys.stderr)
        return 1

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {
                "status": "error"
                if any(i.severity == "error" for i in items)
                else ("warning" if items else "none"),
                "items": [asdict(i) for i in items],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    obs = create_observability()
    duration = elapsed_ms(start)
    for item in items:
        print(f"[{item.severity}] {item.kind}: {item.path} ({item.pattern}) - {item.detail}")
        obs.guard_violation(
            check_id="aiGuards",
            severity=item.severity,
            path=item.path,
            detail=f"{item.kind}: {item.detail}",
        )
    if any(item.severity == "error" for item in items):
        obs.check_failed(
            check_id="aiGuards",
            duration_ms=duration,
            detail="forbidden write or boundary violation",
        )
        return 1
    print(f"guard check completed: {len(items)} warning(s)")
    print(f"report: {REPORT.relative_to(PROJECT_ROOT)}")
    obs.check_passed(check_id="aiGuards", duration_ms=duration, fields={"warnings": len(items)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
