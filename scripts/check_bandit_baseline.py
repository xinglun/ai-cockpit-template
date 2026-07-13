#!/usr/bin/env python3
"""Validate the repository's Bandit low-risk baseline."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / ".ai" / "cockpit" / "bandit_low_risk_baseline.json"


def load_baseline(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("baseline must be a JSON object")
    return data


def current_digest() -> tuple[int, str]:
    result = subprocess.run(
        ["bandit", "-q", "-r", "scripts", "-f", "json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError(result.stderr.strip() or "bandit invocation failed")
    data = json.loads(result.stdout or "{}")
    items = [
        {
            "testId": item["test_id"],
            "severity": item["issue_severity"],
            "filename": Path(item["filename"]).as_posix(),
            "issue": item["issue_text"],
        }
        for item in data.get("results", [])
        if isinstance(item, dict)
    ]
    payload = json.dumps(
        sorted(items, key=lambda item: (item["filename"], item["testId"], item["issue"])),
        sort_keys=True,
    ).encode("utf-8")
    return len(items), hashlib.sha256(payload).hexdigest()


def main() -> int:
    try:
        baseline = load_baseline(BASELINE)
        expected_count = baseline["count"]
        expected_digest = baseline["digest"]
        if (
            not isinstance(expected_count, int)
            or isinstance(expected_count, bool)
            or expected_count < 0
        ):
            raise ValueError("baseline count must be a non-negative integer")
        if not isinstance(expected_digest, str) or not expected_digest:
            raise ValueError("baseline digest must be a non-empty string")
        actual_count, actual_digest = current_digest()
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if (expected_count, expected_digest) != (actual_count, actual_digest):
        print(
            f"[ERROR] bandit baseline drifted: expected count={expected_count} digest={expected_digest}, "
            f"got count={actual_count} digest={actual_digest}",
            file=sys.stderr,
        )
        return 1
    print("bandit low-risk baseline check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
