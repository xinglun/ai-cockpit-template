#!/usr/bin/env python3
"""Verify changed files are covered by Work Item scope."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from ai_common import changed_paths, included, load_json, simple_yaml_lists
from ai_observability import create_observability, elapsed_ms


SCOPE_POLICY = Path(__file__).resolve().parents[1] / ".ai" / "guards" / "scope_policy.yaml"


def string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    return [item for item in value if isinstance(item, str)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Work Item scope against the current diff.")
    parser.add_argument("contract", nargs="?")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.contract:
        print("Skipping scope check (no active contract provided)")
        return 0
    start = time.time()
    try:
        contract = load_json(Path(args.contract))
        paths = changed_paths()
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"Failed to run scope guard: {exc}", file=sys.stderr)
        return 1

    obs = create_observability(work_item_id=contract.get("workItemId", ""))
    scope = string_list(contract, "scope")
    out_of_scope = string_list(contract, "outOfScope")
    policy_lists = simple_yaml_lists(SCOPE_POLICY)
    allow_patterns = policy_lists.get("allowAlways", [])
    destructive = contract.get("destructiveChangePolicy")
    if isinstance(destructive, dict):
        allow_patterns.extend(item for item in destructive.get("allowPatterns", []) if isinstance(item, str))

    issues: list[str] = []
    for path in paths:
        if included(path, allow_patterns):
            continue
        if included(path, out_of_scope):
            issues.append(f"path matches outOfScope: {path}")
        if not included(path, scope):
            issues.append(f"path is not covered by scope: {path}")

    duration = elapsed_ms(start)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        obs.check_failed(check_id="aiScope", duration_ms=duration, detail=f"{len(issues)} issue(s)")
        return 1
    print(f"scope guard passed: {len(paths)} changed path(s) covered")
    obs.check_passed(check_id="aiScope", duration_ms=duration, fields={"changedPaths": len(paths)})
    return 0


if __name__ == "__main__":
    sys.exit(main())

