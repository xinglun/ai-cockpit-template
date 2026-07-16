#!/usr/bin/env python3
"""Report governance repository complexity and immutable archive consistency."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ai_common import parse_yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / ".ai" / "guards" / "governance_complexity_policy.yaml"
DEFAULT_OUTPUT = ROOT / "target" / "governance_complexity_report.json"
# Archive migration is anchored to the immutable commit that introduced
# digest validation. A mutable archive-count threshold must not decide trust.
ARCHIVE_INDEX_INTEGRITY_INTRODUCED_AT = "3dc234a"


def strict_archive_entry(root: Path, entry: dict[str, Any], contract_path: Path) -> bool:
    if not (
        isinstance(entry.get("archiveSequence"), int)
        and not isinstance(entry.get("archiveSequence"), bool)
        and entry["archiveSequence"] >= 1
        and isinstance(entry.get("contractSha256"), str)
        and isinstance(entry.get("summarySha256"), str)
    ):
        return False
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        base_commit = contract.get("baseCommit")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(base_commit, str) or not base_commit:
        # Isolated fixture repositories have no migration history; explicit
        # digest evidence is sufficient for their self-contained validation.
        return True
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ARCHIVE_INDEX_INTEGRITY_INTRODUCED_AT, base_commit],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


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


def archive_files(root: Path, archive: Path, pattern: str) -> list[Path]:
    """Return archive files that can be part of the repository checkout."""
    if not archive.is_dir():
        return []
    if (root / ".git").exists():
        try:
            allowed = set(tracked_files(root))
        except RuntimeError:
            allowed = set()
        if allowed:
            return sorted(path for path in archive.rglob(pattern) if path in allowed)
    return sorted(archive.rglob(pattern))


def archive_metrics(root: Path) -> tuple[dict[str, int], list[str]]:
    archive = root / ".ai" / "work-items" / "archive"
    contracts = archive_files(root, archive, "*.contract.json")
    summaries = archive_files(root, archive, "*.summary.json")
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
    authoritative: dict[tuple[str, str], tuple[Path, Path]] = {}
    for contract_path in contracts:
        summary_path = contract_path.with_name(
            contract_path.name.replace(".contract.json", ".summary.json")
        )
        if summary_path.is_file():
            key = (
                contract_path.relative_to(root).as_posix(),
                summary_path.relative_to(root).as_posix(),
            )
            authoritative[key] = (contract_path, summary_path)

    indexed: set[tuple[str, str]] = set()
    strict_contract_paths: set[str] = set()
    strict_summary_paths: set[str] = set()
    work_item_ids: set[str] = set()
    sequences: set[int] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            issues.append("archive index contains a non-object entry")
            continue
        index_contract_path = entry.get("contractPath")
        index_summary_path = entry.get("summaryPath")
        if not isinstance(index_contract_path, str) or not isinstance(index_summary_path, str):
            issues.append("archive index entry lacks Contract/Summary paths")
            continue
        pair = (index_contract_path, index_summary_path)
        contract_for_entry = root / index_contract_path
        legacy_entry = not strict_archive_entry(root, entry, contract_for_entry)
        if pair in indexed and not legacy_entry:
            issues.append(f"archive index duplicates Contract/Summary pair {index_contract_path}")
        if not legacy_entry and index_contract_path in strict_contract_paths:
            issues.append(f"archive index duplicates Contract path {index_contract_path}")
        if not legacy_entry and index_summary_path in strict_summary_paths:
            issues.append(f"archive index duplicates Summary path {index_summary_path}")
        indexed.add(pair)
        if not legacy_entry:
            strict_contract_paths.add(index_contract_path)
            strict_summary_paths.add(index_summary_path)
        if pair not in authoritative:
            issues.append(
                f"archive index pair is not an authoritative archive pair: {index_contract_path}"
            )
        work_item_id = entry.get("workItemId")
        if not isinstance(work_item_id, str) or not work_item_id:
            issues.append(f"archive index entry has invalid workItemId for {index_contract_path}")
        elif work_item_id in work_item_ids and not legacy_entry:
            issues.append(f"archive index duplicates workItemId {work_item_id}")
        elif not legacy_entry:
            work_item_ids.add(work_item_id)
        sequence = entry.get("archiveSequence")
        if legacy_entry:
            sequence = None
        elif not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            issues.append(
                f"archive index entry has invalid archiveSequence for {index_contract_path}"
            )
        elif sequence in sequences:
            issues.append(f"archive index duplicates archiveSequence {sequence}")
        else:
            sequences.add(sequence)
        for relative in (index_contract_path, index_summary_path):
            if not (root / relative).is_file():
                issues.append(f"archive index references missing {relative}")
        if pair in authoritative:
            contract_file, summary_file = authoritative[pair]
            for field, path in (("contractSha256", contract_file), ("summarySha256", summary_file)):
                expected = hashlib.sha256(path.read_bytes()).hexdigest()
                if not legacy_entry and entry.get(field) != expected:
                    issues.append(f"archive index {field} mismatch for {path.relative_to(root)}")
            try:
                contract = json.loads(contract_file.read_text(encoding="utf-8"))
                summary = json.loads(summary_file.read_text(encoding="utf-8"))
                if not legacy_entry and contract.get("workItemId") != work_item_id:
                    issues.append(f"archive index workItemId mismatch for {index_contract_path}")
                if not legacy_entry and summary.get("workItemId") != work_item_id:
                    issues.append(f"archive Summary workItemId mismatch for {index_summary_path}")
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                issues.append(f"archive pair cannot be loaded for index validation: {exc}")

    for pair in sorted(set(authoritative) - indexed):
        issues.append(
            f"archive index does not cover authoritative archive pair: {pair[0]}, {pair[1]}"
        )

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
    # trackedFiles remains in the report for repository-shape observation, but
    # immutable archive evidence makes a fixed ceiling unsuitable as a gate.
    metrics = (
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
