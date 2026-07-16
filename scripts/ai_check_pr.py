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
# Worktree-bound verification evidence became mandatory at this migration point.
# Archives created before it remain immutable historical evidence.
WORKTREE_DIGEST_INTRODUCED_AT = "63ec6fcd3c8f945b379966d43457e44ccaeba258"
# New archive pairs use explicit ordering evidence. Older pairs remain readable
# through the timestamp fallback and are never rewritten in place.
ARCHIVE_SEQUENCE_INTRODUCED_AT = "f0b7caa9fdc8fa0bc25cf8c099fc2cef5f0c61b7"
NEW_WORK_ITEM_SEQUENCE = 74


def _git_blob_hash(revision: str, path: str) -> str:
    """Return the git object hash of *path* at *revision*, or empty string on error."""
    result = run_git(["rev-parse", f"{revision}:{path}"])
    return result.stdout.strip() if result.returncode == 0 else ""


def _worktree_blob_hash(path: str) -> str:
    """Return the git blob hash for the current worktree copy of *path*."""
    result = run_git(["hash-object", "--no-filters", path])
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_records(output: str) -> list[str]:
    if "\0" in output:
        return [item for item in output.split("\0") if item]
    return [line for line in output.splitlines() if line]


def _is_no_op_restore(base: str, path: str) -> bool:
    """Return True if the worktree restores *path* to an allowed PR baseline blob.

    This handles the case where an archive file was accidentally modified in a
    previous commit and the current change restores it to the merge-base content
    or to the direct parent of that base. The latter is needed when the PR base
    already contains the accidental archive edit. The archive integrity is fully
    preserved so append-only policy should not flag it.
    """
    worktree_blob = _worktree_blob_hash(path)
    if not worktree_blob:
        return False
    for revision in (base, f"{base}^"):
        baseline_blob = _git_blob_hash(revision, path)
        if baseline_blob and baseline_blob == worktree_blob:
            return True
    return False


def archive_evidence_changes(base: str) -> dict[str, str]:
    result: dict[str, str] = {}
    diff = run_git(["diff", "--name-status", "-z", f"{base}...HEAD"])
    saw_archive_evidence = False
    if diff.returncode == 0:
        ordered_changes: list[tuple[str, str]] = []
        records = _git_records(diff.stdout)
        if records and "\t" in records[0]:
            for line in records:
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                status = parts[0]
                if status.startswith(("R", "C")) and len(parts) >= 3:
                    ordered_changes.extend([("D", parts[1]), (parts[0], parts[2])])
                else:
                    ordered_changes.append((status, parts[-1]))
        else:
            i = 0
            while i < len(records):
                status = records[i]
                i += 1
                if status.startswith(("R", "C")):
                    if i + 1 >= len(records):
                        break
                    ordered_changes.extend([("D", records[i]), (status, records[i + 1])])
                    i += 2
                    continue
                if i >= len(records):
                    break
                ordered_changes.append((status, records[i]))
                i += 1
    else:
        ordered_changes = changed_name_status(
            {"baseCommit": base, "baselineDirtyPaths": []}, ignore_baseline_dirty=True
        )
    for status, path in ordered_changes:
        if not (path.startswith(ARCHIVE_PREFIX) and path.endswith(ARCHIVE_SUFFIXES)):
            continue
        # A later commit may restore a historical archive file to the exact
        # parent blob. It is not new evidence and must not become a PR owner.
        if status == "M" and _is_no_op_restore(base, path):
            continue
        saw_archive_evidence = True
        result[path] = status
    if not saw_archive_evidence:
        for status, path in changed_name_status(
            {"baseCommit": base, "baselineDirtyPaths": []}, ignore_baseline_dirty=True
        ):
            if not (path.startswith(ARCHIVE_PREFIX) and path.endswith(ARCHIVE_SUFFIXES)):
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


def archive_pair_rank(contract_path: Path, summary_path: Path) -> tuple[int, str, str]:
    try:
        contract_rel = contract_path.relative_to(PROJECT_ROOT).as_posix()
        summary_rel = summary_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return 0, contract_path.as_posix(), summary_path.as_posix()
    try:
        summary = load_json(summary_path)
    except (OSError, ValueError, json.JSONDecodeError):
        summary = {}
    sequence = summary.get("archiveSequence") if isinstance(summary, dict) else None
    if isinstance(sequence, int) and not isinstance(sequence, bool) and sequence > 0:
        return sequence, contract_rel, summary_rel
    result = run_git(["log", "-1", "--format=%ct", "--", contract_rel, summary_rel])
    if result.returncode != 0:
        return 0, contract_rel, summary_rel
    try:
        timestamp = int(result.stdout.strip())
    except ValueError:
        timestamp = 0
    return timestamp, contract_rel, summary_rel


def archive_sequence_required(contract: dict[str, Any]) -> bool:
    base_commit = contract.get("baseCommit")
    if not isinstance(base_commit, str) or not base_commit:
        return False
    result = run_git(["merge-base", "--is-ancestor", ARCHIVE_SEQUENCE_INTRODUCED_AT, base_commit])
    return result.returncode == 0


def archive_sequence_issue(contract: dict[str, Any], summary: dict[str, Any]) -> str | None:
    if not archive_sequence_required(contract):
        return None
    sequence = summary.get("archiveSequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        return "archiveSequence must be a positive integer for new archive evidence"
    return None


def is_legacy_archive(contract: dict[str, Any], summary: dict[str, Any]) -> bool:
    """Return whether an archive pair predates strict worktree evidence."""
    if summary.get("summaryVersion") != 2:
        return True
    base_commit = contract.get("baseCommit")
    if not isinstance(base_commit, str) or not base_commit:
        return False
    result = run_git(["merge-base", "--is-ancestor", WORKTREE_DIGEST_INTRODUCED_AT, base_commit])
    return result.returncode != 0


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
    changed_stems = dict.fromkeys(
        archive_stem(path) for path, status in evidence_changes.items() if status == "A"
    )
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

    archive_entries: list[tuple[Path, dict[str, Any], dict[str, Any], tuple[int, str, str]]] = []
    audit_paths: set[str] = set()
    for contract_path in list(dict.fromkeys(contract_paths)):
        summary_path = Path(str(contract_path).replace(".contract.json", ".summary.json"))
        if not contract_path.exists():
            issues.append(
                f"archived Contract is missing or deleted: {contract_path.relative_to(PROJECT_ROOT)}"
            )
            continue
        if not summary_path.exists():
            issues.append(
                f"archived Contract is missing Summary: {summary_path.relative_to(PROJECT_ROOT)}"
            )
            continue
        try:
            contract = load_json(contract_path)
            summary = load_json(summary_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            issues.append(f"failed to load archive pair {contract_path}: {exc}")
            continue
        archive_entries.append(
            (contract_path, contract, summary, archive_pair_rank(contract_path, summary_path))
        )
        contract_rel = contract_path.relative_to(PROJECT_ROOT).as_posix()
        summary_rel = summary_path.relative_to(PROJECT_ROOT).as_posix()
        audit_paths.update({contract_rel, summary_rel})
        if contract.get("contractVersion") != 2:
            issues.append(f"{contract_rel}: PR archive evidence requires contractVersion 2")
        issues.extend(f"{contract_rel}: {issue}" for issue in validate_contract(contract))
        legacy_archive = is_legacy_archive(contract, summary)
        issues.extend(
            f"{summary_rel}: {issue}"
            for issue in validate_summary(
                summary,
                contract,
                expected_contract_hash=hashlib.sha256(contract_path.read_bytes()).hexdigest(),
                contract_path=contract_rel,
                summary_path=summary_rel,
                legacy_archive=legacy_archive,
            )
        )
        sequence_issue = archive_sequence_issue(contract, summary)
        if sequence_issue:
            issues.append(f"{summary_rel}: {sequence_issue}")
        issues.extend(f"{contract_rel}: {issue}" for issue in machine_path_issues(contract))
        issues.extend(f"{summary_rel}: {issue}" for issue in machine_path_issues(summary))

    archive_entries.sort(key=lambda entry: entry[3])

    new_work_items = {
        summary.get("workItemId")
        for _path, contract, summary, _rank in archive_entries
        if isinstance(summary.get("archiveSequence"), int)
        and summary.get("archiveSequence", 0) >= NEW_WORK_ITEM_SEQUENCE
        and contract.get("workItemId")
    }
    if len(new_work_items) > 1:
        issues.append(
            "PR must contain exactly one newly maintained Work Item; "
            f"found {len(new_work_items)}: {', '.join(sorted(str(item) for item in new_work_items))}"
        )

    sequences: dict[int, str] = {}
    for contract_path, contract, summary, _rank in archive_entries:
        if not archive_sequence_required(contract):
            continue
        sequence = summary.get("archiveSequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            continue
        contract_rel = contract_path.relative_to(PROJECT_ROOT).as_posix()
        previous = sequences.get(sequence)
        if previous is not None:
            issues.append(
                f"archiveSequence {sequence} is duplicated by {previous} and {contract_rel}"
            )
        else:
            sequences[sequence] = contract_rel

    all_paths = changed_paths(
        {"baseCommit": base, "baselineDirtyPaths": []}, ignore_baseline_dirty=True
    )
    policy = simple_yaml_lists(SCOPE_POLICY)
    ownership = parse_simple_manifest(OWNERSHIP_POLICY)
    exempt = policy.get("allowAlways", [])

    generated_archive_index = f"{ARCHIVE_PREFIX}index.json"

    def is_archived_generated_evidence(path: str) -> bool:
        """Accept generated archive metadata only when archived evidence names it."""
        return path == generated_archive_index and any(
            path in changed_file_paths(summary)
            for _contract_path, _contract, summary, _rank in archive_entries
        )

    for path in all_paths:
        if path in audit_paths or included(path, exempt) or path in no_op_restore_paths:
            continue
        owners = [
            entry
            for entry in archive_entries
            if included(
                path, [pattern for pattern in entry[1].get("scope", []) if isinstance(pattern, str)]
            )
            and not included(
                path,
                [pattern for pattern in entry[1].get("outOfScope", []) if isinstance(pattern, str)],
            )
            and path in changed_file_paths(entry[2])
        ]
        if not owners:
            if is_archived_generated_evidence(path):
                continue
            issues.append(
                f"complete PR diff path lacks paired ownership (same Contract scope and Summary changedFiles): {path}"
            )
            continue
        # The PR audit resolves overlapping archive claims by the stable archive rank.
        _, effective_contract, _, _ = owners[-1]
        owner_match = first_match(path, ownership)
        if owner_match:
            _, owner = owner_match
            if owner.get("aiWrite") == "forbidden":
                issues.append(f"complete PR diff contains forbidden write: {path}")
            if owner.get("aiWrite") == "restricted" and not (
                isinstance(effective_contract.get("restrictedWriteApproval"), dict)
                and effective_contract["restrictedWriteApproval"].get("approved") is True
            ):
                issues.append(
                    f"complete PR diff restricted path lacks approval in a covering Contract: {path}"
                )
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
    contract_paths = [Path(path).resolve() for path in args.contracts] or archived_contract_paths(
        args.base
    )
    issues = validate_pr_bundle(args.base, contract_paths)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print(f"aggregate PR check passed: {len(contract_paths)} Work Item(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
