#!/usr/bin/env python3
"""Validate all changed archived Work Items against the complete PR diff."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from ai_check_summary import changed_file_paths, validate_summary
from ai_check_work_item import validate_contract
from ai_common import (
    PROJECT_ROOT,
    changed_name_status,
    changed_paths,
    contains_machine_path,
    first_match,
    included,
    load_json,
    parse_simple_manifest,
    run_git,
    simple_yaml_lists,
)


SCOPE_POLICY = PROJECT_ROOT / ".ai" / "guards" / "scope_policy.yaml"
OWNERSHIP_POLICY = PROJECT_ROOT / ".ai" / "guards" / "file_ownership.yaml"


ARCHIVE_PREFIX = ".ai/work-items/archive/"
ARCHIVE_SUFFIXES = (".contract.json", ".summary.json", ".review.json")


def _git_blob_hash(revision: str, path: str) -> str:
    """Return the git object hash of *path* at *revision*, or empty string on error."""
    result = run_git(["rev-parse", f"{revision}:{path}"])
    return result.stdout.strip() if result.returncode == 0 else ""


def _is_no_op_restore(base: str, path: str) -> bool:
    """Return True if *path* was changed at *base* but HEAD restores it to the pre-base state.

    This handles the case where an archive file was accidentally modified in *base*
    and a subsequent commit restores it to its original content.  The archive
    integrity is fully preserved so the append-only policy should not flag it.
    """
    head_blob = _git_blob_hash("HEAD", path)
    if not head_blob:
        return False
    # Walk backwards from base^ to find the most recent ancestor that had the
    # same blob.  If base^ already has the same blob, the restore is clean.
    parent_blob = _git_blob_hash(f"{base}^", path)
    return bool(parent_blob) and parent_blob == head_blob


def archive_evidence_changes(base: str) -> dict[str, str]:
    changes = changed_name_status(
        {"baseCommit": base, "baselineDirtyPaths": []}, ignore_baseline_dirty=True
    )
    result: dict[str, str] = {}
    for status, path in changes:
        if not (path.startswith(ARCHIVE_PREFIX) and path.endswith(ARCHIVE_SUFFIXES)):
            continue
        # A no-op restoration: M-status file whose blob at HEAD matches the blob
        # at base^ (i.e., the file was accidentally changed at base and the
        # current HEAD restores it to the pre-base state).  Archive integrity is
        # fully preserved, so exclude it from the evidence map.
        if status == "M" and _is_no_op_restore(base, path):
            continue
        result[path] = status
    return result


def archive_stem(path: str) -> str:
    for suffix in ARCHIVE_SUFFIXES:
        if path.endswith(suffix):
            return path[: -len(suffix)]
    raise ValueError(f"not an archive evidence path: {path}")


def archived_contract_paths(base: str) -> list[Path]:
    stems = dict.fromkeys(archive_stem(path) for path in archive_evidence_changes(base))
    return [PROJECT_ROOT / f"{stem}.contract.json" for stem in stems]


def machine_path_issues(value: Any, location: str = "root") -> list[str]:
    issues: list[str] = []
    if isinstance(value, str) and contains_machine_path(value):
        issues.append(f"{location} contains a machine-specific path")
    elif isinstance(value, dict):
        for key, child in value.items():
            issues.extend(machine_path_issues(child, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(machine_path_issues(child, f"{location}[{index}]"))
    return issues


def validate_pr_bundle(base: str, contract_paths: list[Path]) -> list[str]:
    issues: list[str] = []
    evidence_changes = archive_evidence_changes(base)
    changed_stems = dict.fromkeys(archive_stem(path) for path in evidence_changes)
    discovered_contracts = [
        PROJECT_ROOT / f"{archive_stem(path)}.contract.json"
        for path in evidence_changes
        if path.startswith(ARCHIVE_PREFIX) and path.endswith(ARCHIVE_SUFFIXES)
    ]
    contract_paths = list(dict.fromkeys([*contract_paths, *discovered_contracts]))

    # Collect no-op restore paths so they are exempt from the ownership check below.
    all_archive_changes = changed_name_status(
        {"baseCommit": base, "baselineDirtyPaths": []}, ignore_baseline_dirty=True
    )
    no_op_restore_paths: set[str] = {
        path
        for status, path in all_archive_changes
        if path.startswith(ARCHIVE_PREFIX)
        and path.endswith(ARCHIVE_SUFFIXES)
        and status == "M"
        and _is_no_op_restore(base, path)
    }

    for path, status in sorted(evidence_changes.items()):
        if status != "A":
            issues.append(
                f"archive PR policy is append-only; existing evidence path has status {status}: {path}"
            )
    for stem in sorted(changed_stems):
        contract_rel = f"{stem}.contract.json"
        summary_rel = f"{stem}.summary.json"
        if evidence_changes.get(contract_rel) != "A" or evidence_changes.get(summary_rel) != "A":
            issues.append(
                "new archive evidence must add its Contract and Summary together: "
                f"{contract_rel}, {summary_rel}"
            )

    if not contract_paths:
        return ["PR diff must contain at least one archived Work Item Contract"]

    contracts: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    audit_paths: set[str] = set()
    for contract_path in sorted(set(contract_paths)):
        summary_path = Path(str(contract_path).replace(".contract.json", ".summary.json"))
        if not contract_path.exists():
            issues.append(
                f"archived Contract is missing or deleted: {contract_path.relative_to(PROJECT_ROOT)}"
            )
            continue
        if not summary_path.exists():
            issues.append(f"archived Contract is missing Summary: {summary_path.relative_to(PROJECT_ROOT)}")
            continue
        try:
            contract = load_json(contract_path)
            summary = load_json(summary_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            issues.append(f"failed to load archive pair {contract_path}: {exc}")
            continue
        contracts.append(contract)
        summaries.append(summary)
        contract_rel = contract_path.relative_to(PROJECT_ROOT).as_posix()
        summary_rel = summary_path.relative_to(PROJECT_ROOT).as_posix()
        audit_paths.update({contract_rel, summary_rel})
        if contract.get("contractVersion") != 2:
            issues.append(f"{contract_rel}: PR archive evidence requires contractVersion 2")
        issues.extend(f"{contract_rel}: {issue}" for issue in validate_contract(contract))
        issues.extend(
            f"{summary_rel}: {issue}"
            for issue in validate_summary(
                summary,
                contract,
                expected_contract_hash=hashlib.sha256(contract_path.read_bytes()).hexdigest(),
                contract_path=contract_rel,
                summary_path=summary_rel,
            )
        )
        issues.extend(f"{contract_rel}: {issue}" for issue in machine_path_issues(contract))
        issues.extend(f"{summary_rel}: {issue}" for issue in machine_path_issues(summary))

    all_paths = changed_paths(
        {"baseCommit": base, "baselineDirtyPaths": []}, ignore_baseline_dirty=True
    )
    policy = simple_yaml_lists(SCOPE_POLICY)
    ownership = parse_simple_manifest(OWNERSHIP_POLICY)
    exempt = policy.get("allowAlways", [])
    pairs = list(zip(contracts, summaries, strict=True))

    for path in all_paths:
        if path in audit_paths or included(path, exempt) or path in no_op_restore_paths:
            continue
        owners = [
            (contract, summary)
            for contract, summary in pairs
            if included(path, [pattern for pattern in contract.get("scope", []) if isinstance(pattern, str)])
            and not included(path, [pattern for pattern in contract.get("outOfScope", []) if isinstance(pattern, str)])
            and path in changed_file_paths(summary)
        ]
        if not owners:
            issues.append(
                f"complete PR diff path lacks paired ownership (same Contract scope and Summary changedFiles): {path}"
            )
            continue
        # The PR audit resolves overlapping archive claims deterministically:
        # the latest matching archive pair in the PR wins for a given path.
        effective_contract, _ = owners[-1]
        owner_match = first_match(path, ownership)
        if owner_match:
            _, owner = owner_match
            if owner.get("aiWrite") == "forbidden":
                issues.append(f"complete PR diff contains forbidden write: {path}")
            if owner.get("aiWrite") == "restricted" and not (
                isinstance(effective_contract.get("restrictedWriteApproval"), dict)
                and effective_contract["restrictedWriteApproval"].get("approved") is True
            ):
                issues.append(f"complete PR diff restricted path lacks approval in a covering Contract: {path}")
    return issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=os.environ.get("AI_BASE_COMMIT", ""))
    parser.add_argument("contracts", nargs="*")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.base:
        print("ERROR: --base or AI_BASE_COMMIT is required", file=sys.stderr)
        return 2
    contract_paths = [Path(path).resolve() for path in args.contracts] or archived_contract_paths(args.base)
    issues = validate_pr_bundle(args.base, contract_paths)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print(f"aggregate PR check passed: {len(contract_paths)} Work Item(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
