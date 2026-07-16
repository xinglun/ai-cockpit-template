#!/usr/bin/env python3
"""Report governance repository complexity and immutable archive consistency."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ai_common import parse_yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / ".ai" / "guards" / "governance_complexity_policy.yaml"
DEFAULT_OUTPUT = ROOT / "target" / "governance_complexity_report.json"


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise RuntimeError("git ls-files failed")
    return [root / item for item in result.stdout.split("\0") if item]


def line_count(paths: list[Path], suffix: str) -> int:
    total = 0
    for path in paths:
        if path.suffix.lower() != suffix or not path.is_file():
            continue
        try:
            total += len(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            continue
    return total


def archive_metrics(root: Path) -> tuple[dict[str, int], list[str]]:
    archive = root / ".ai" / "work-items" / "archive"
    contracts = sorted(archive.rglob("*.contract.json")) if archive.is_dir() else []
    summaries = sorted(archive.rglob("*.summary.json")) if archive.is_dir() else []
    contract_stems = {path.name.removesuffix(".contract.json") for path in contracts}
    summary_stems = {path.name.removesuffix(".summary.json") for path in summaries}
    issues = [
        f"missing paired Summary for {stem}" for stem in sorted(contract_stems - summary_stems)
    ]
    issues.extend(
        f"missing paired Contract for {stem}" for stem in sorted(summary_stems - contract_stems)
    )

    index_path = archive / "index.json"
    entries: list[dict[str, Any]] = []
    if not index_path.is_file():
        issues.append("archive index is missing")
    else:
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
            entries = raw.get("entries", []) if isinstance(raw, dict) else []
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(f"archive index cannot be loaded: {exc}")
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        contract_path = entry.get("contractPath")
        summary_path = entry.get("summaryPath")
        if not isinstance(contract_path, str) or not isinstance(summary_path, str):
            issues.append("archive index entry lacks Contract/Summary paths")
            continue
        for relative in (contract_path, summary_path):
            if not (root / relative).is_file():
                issues.append(f"archive index references missing {relative}")
    return {
        "archiveContracts": len(contracts),
        "archiveSummaries": len(summaries),
        "archiveIndexEntries": len(entries),
    }, issues


def load_policy(path: Path) -> dict[str, int]:
    raw = parse_yaml(path)
    if not isinstance(raw, dict) or not isinstance(raw.get("max"), dict):
        raise ValueError("policy must contain a max mapping")
    values = raw["max"]
    metrics = (
        "trackedFiles",
        "pythonLines",
        "markdownLines",
    )
    result: dict[str, int] = {}
    for metric in metrics:
        value = values.get(metric)
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = 0
        if value < 1:
            raise ValueError(f"max.{metric} must be a positive integer")
        result[metric] = value
    return result


def build_report(root: Path, policy_path: Path) -> tuple[dict[str, Any], list[str]]:
    files = tracked_files(root)
    archive, archive_issues = archive_metrics(root)
    metrics = {
        "trackedFiles": len(files),
        "pythonLines": line_count(files, ".py"),
        "markdownLines": line_count(files, ".md"),
        **archive,
    }
    limits = load_policy(policy_path)
    issues = list(archive_issues)
    issues.extend(
        f"{metric}={metrics[metric]} exceeds configured maximum {limit}"
        for metric, limit in limits.items()
        if metrics[metric] > limit
    )
    return {
        "reportVersion": 1,
        "policy": str(policy_path.relative_to(root)),
        "metrics": metrics,
        "limits": limits,
        "issues": issues,
    }, issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    policy = Path(args.policy).resolve()
    output = Path(args.output).resolve()
    try:
        report, issues = build_report(root, policy)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"[ERROR] governance complexity report failed: {exc}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print(f"governance complexity check passed: {report['metrics']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
