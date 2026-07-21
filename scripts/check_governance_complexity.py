#!/usr/bin/env python3
"""Report governance repository complexity and immutable archive consistency."""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
import os
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


def complexity_files(root: Path, paths: list[Path]) -> list[Path]:
    """Exclude generated Cockpit status from persistent complexity budgets."""
    generated_status = root / ".ai" / "cockpit" / "current_status.md"
    return [path for path in paths if path != generated_status]


def file_count(paths: list[Path], predicate: Any) -> int:
    return sum(1 for path in paths if path.is_file() and predicate(path))


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
                manifest_path = entry.get("manifestPath")
                manifest_digest = entry.get("manifestSha256")
                if manifest_path is not None or manifest_digest is not None:
                    manifest_file = root / str(manifest_path)
                    if not isinstance(manifest_path, str) or not manifest_file.is_file():
                        issues.append(f"archive manifest is missing for {index_contract_path}")
                    elif hashlib.sha256(manifest_file.read_bytes()).hexdigest() != manifest_digest:
                        issues.append(f"archive manifestSha256 mismatch for {index_contract_path}")
                    else:
                        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                        if (
                            not isinstance(manifest, dict)
                            or manifest.get("format") != "ai-cockpit-archive-manifest"
                        ):
                            issues.append(
                                f"archive manifest has invalid format for {index_contract_path}"
                            )
                        if (
                            not isinstance(manifest, dict)
                            or manifest.get("contractSha256")
                            != hashlib.sha256(contract_file.read_bytes()).hexdigest()
                        ):
                            issues.append(
                                f"archive manifest Contract digest mismatch for {index_contract_path}"
                            )
                        if (
                            not isinstance(manifest, dict)
                            or manifest.get("summarySha256")
                            != hashlib.sha256(summary_file.read_bytes()).hexdigest()
                        ):
                            issues.append(
                                f"archive manifest Summary digest mismatch for {index_summary_path}"
                            )
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


def function_complexity(paths: list[Path]) -> int:
    """Return the maximum deterministic branch complexity of a Python function."""
    maximum = 0
    for path in paths:
        if path.suffix.lower() != ".py" or not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            branches = sum(
                isinstance(item, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Match))
                for item in ast.walk(node)
            )
            maximum = max(maximum, 1 + branches)
    return maximum


def repository_shape_metrics(
    root: Path, files: list[Path], archive: dict[str, int]
) -> dict[str, Any]:
    schema_count = sum(
        1 for path in files if ".ai/trust/schema/" in path.as_posix() and path.suffix == ".json"
    )
    guard_count = sum(1 for path in files if ".ai/guards/" in path.as_posix() and path.is_file())
    field_counts: Counter[str] = Counter()
    for path in files:
        if not path.name.endswith(".contract.json"):
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            field_counts.update(value.keys())
    repeated_fields = sum(1 for count in field_counts.values() if count > 1)
    graph: dict[str, set[str]] = defaultdict(set)
    script_names = {
        path.stem for path in files if path.parent.name == "scripts" and path.suffix == ".py"
    }
    for path in files:
        if path.parent.name != "scripts" or path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            else:
                continue
            graph[path.stem].update(name for name in names if name in script_names)
    cycles = 0
    for start in graph:
        stack = [(start, {start})]
        while stack:
            current, seen = stack.pop()
            for target in graph.get(current, set()):
                if target == start:
                    cycles += 1
                elif target not in seen:
                    stack.append((target, seen | {target}))
    allowlist_entries = sum(
        1
        for path in files
        if path.name == "install_ai_cockpit.py"
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if "allow" in line.lower()
    )
    total_evidence = 0
    generated_evidence = 0
    archive_dir = root / ".ai" / "work-items" / "archive"
    for summary in archive_files(root, archive_dir, "*.summary.json"):
        try:
            value = json.loads(summary.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        for record in value.get("verification", []) if isinstance(value, dict) else []:
            if not isinstance(record, dict):
                continue
            total_evidence += 1
            generated_evidence += int("executionContractPath" in record)
    evidence_ratio = generated_evidence / total_evidence if total_evidence else 0.0
    return {
        "functionComplexity": function_complexity(files),
        "schemaCount": schema_count,
        "guardCount": guard_count,
        "repeatedProtocolFields": repeated_fields,
        "dependencyCycles": cycles,
        "installAllowlistEntries": allowlist_entries,
        "archiveGrowth": archive.get("archiveContracts", 0),
        "generatedEvidenceRatio": round(evidence_ratio, 6),
    }


def load_policy(path: Path) -> tuple[dict[str, float], dict[str, float], list[str]]:
    raw = parse_yaml(path)
    if not isinstance(raw, dict) or not isinstance(raw.get("max"), dict):
        raise ValueError("policy must contain a max mapping")
    values = raw["max"]
    metrics = tuple(metric for metric in values.keys() if metric != "trackedFiles")
    result: dict[str, float] = {}
    for metric in metrics:
        value = values[metric]
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"max.{metric} must be numeric") from None
        if value < 0:
            raise ValueError(f"max.{metric} must be non-negative")
        result[metric] = value
    baseline_raw = raw.get("baseline", {})
    baseline: dict[str, float] = {}
    if isinstance(baseline_raw, dict):
        for metric, value in baseline_raw.items():
            try:
                baseline[metric] = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"baseline.{metric} must be numeric") from None
    records = raw.get("repaymentRecords", [])
    return result, baseline, records if isinstance(records, list) else []


def repayment_issues(
    limits: dict[str, float], baseline: dict[str, float], records: list[Any]
) -> list[str]:
    issues: list[str] = []
    for metric, limit in limits.items():
        previous = baseline.get(metric)
        if previous is None or limit <= previous:
            continue
        matched = False
        for record in records:
            parts = str(record).split("|", 6)
            if len(parts) < 6:
                continue
            _, record_metric, old, new, owner, due_date, *_ = parts
            if (
                record_metric == metric
                and float(old) == previous
                and float(new) == limit
                and owner.strip()
                and due_date.strip()
            ):
                matched = True
                break
        if not matched:
            issues.append(
                f"{metric} budget increase {previous:g}->{limit:g} lacks owner/due-date repayment record"
            )
    return issues


def resolve_baseline_commit(root: Path, revision: str) -> dict[str, str]:
    """Resolve a baseline revision or preserve an explicit unavailable state."""
    result = subprocess.run(
        ["git", "rev-parse", revision], cwd=root, capture_output=True, text=True, check=False
    )  # nosec B603 B607
    if result.returncode == 0 and result.stdout.strip():
        return {"status": "resolved", "commit": result.stdout.strip(), "source": revision}
    return {"status": "unavailable", "reason": f"Cannot resolve baseline revision: {revision}"}


def baseline_evidence(root: Path) -> dict[str, dict[str, str]]:
    """Bind Adoption, Active, and Work Item baseline identities to repository facts."""
    adoption_revision = os.environ.get("AI_COMPLEXITY_ADOPTION_BASE_COMMIT", "").strip()
    if adoption_revision:
        adoption = resolve_baseline_commit(root, adoption_revision)
    else:
        adoption = {
            "status": "unavailable",
            "reason": "Adoption baseline was not supplied by the adopter.",
        }
    active_revision = os.environ.get("AI_COMPLEXITY_ACTIVE_BASE_COMMIT", "origin/main").strip()
    active = resolve_baseline_commit(root, active_revision)
    work_item_revision = os.environ.get("AI_COMPLEXITY_WORK_ITEM_BASE_COMMIT", "").strip()
    if not work_item_revision:
        contract_path = root / ".ai" / "work-items" / "active"
        contracts = sorted(contract_path.glob("*.contract.json")) if contract_path.is_dir() else []
        if len(contracts) == 1:
            try:
                contract = json.loads(contracts[0].read_text(encoding="utf-8"))
                work_item_revision = str(contract.get("baseCommit", "")).strip()
            except (OSError, json.JSONDecodeError):
                work_item_revision = ""
    work_item = (
        resolve_baseline_commit(root, work_item_revision)
        if work_item_revision
        else {"status": "unavailable", "reason": "No active Work Item base commit was supplied."}
    )
    return {"adoption": adoption, "active": active, "workItem": work_item}


def policy_activation(policy_path: Path) -> dict[str, str]:
    """Expose whether a complexity policy is proposed or explicitly confirmed."""
    raw = parse_yaml(policy_path)
    proposal = raw.get("proposal", {}) if isinstance(raw, dict) else {}
    if not isinstance(proposal, dict) or proposal.get("status") not in {"proposed", "confirmed"}:
        return {"status": "unavailable", "reason": "Policy activation state is not declared."}
    result = {"status": str(proposal["status"])}
    for key in ("confirmedBy", "reason", "contractHash", "preflightHash"):
        if proposal.get(key):
            result[key] = str(proposal[key])
    return result


def build_report(root: Path, policy_path: Path) -> tuple[dict[str, Any], list[str]]:
    files = tracked_files(root)
    measured_files = complexity_files(root, files)
    archive, archive_issues = archive_metrics(root)
    metrics = {
        "trackedFiles": len(files),
        "pythonLines": line_count(files, ".py"),
        "markdownLines": line_count(measured_files, ".md"),
        "pythonFiles": file_count(files, lambda path: path.suffix.lower() == ".py"),
        "markdownFiles": file_count(measured_files, lambda path: path.suffix.lower() == ".md"),
        "governanceScripts": file_count(
            files, lambda path: path.parent.name == "scripts" and path.name.startswith("ai_")
        ),
        "guardFiles": file_count(files, lambda path: ".ai/guards/" in path.as_posix()),
        **archive,
    }
    metrics.update(repository_shape_metrics(root, files, archive))
    baseline = int(os.environ.get("AI_COMPLEXITY_BASELINE_PYTHON_LINES", metrics["pythonLines"]))
    limits, policy_baseline, repayment_records = load_policy(policy_path)
    issues = list(archive_issues)
    issues.extend(
        f"{metric}={metrics[metric]} exceeds configured maximum {limit:g}"
        for metric, limit in limits.items()
        if metric in metrics and metrics[metric] > limit
    )
    issues.extend(repayment_issues(limits, policy_baseline, repayment_records))
    return {
        "reportVersion": 2,
        "policy": str(policy_path.relative_to(root)),
        "metrics": metrics,
        "limits": limits,
        "complexityDelta": {
            "pythonLines": metrics["pythonLines"] - baseline,
            "budgetIncreases": {
                metric: limits[metric] - policy_baseline[metric]
                for metric in limits
                if metric in policy_baseline and limits[metric] > policy_baseline[metric]
            },
        },
        "baselineEvidence": baseline_evidence(root),
        "policyActivation": policy_activation(policy_path),
        "classification": {
            "historicalDebt": {
                "status": "unavailable",
                "reason": "Historical metric snapshot is not available.",
            },
            "workItemDelta": {
                "status": "unavailable",
                "reason": "Work Item-start metric snapshot is not available.",
            },
            "deterioration": {
                "status": "unavailable",
                "reason": "A comparable prior metric snapshot is not available.",
            },
        },
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
