#!/usr/bin/env python3
"""Preview Work Item ownership for every path in a local or PR diff."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_check_summary import changed_file_paths
from ai_check_pr import archive_evidence_changes
from ai_common import PROJECT_ROOT, changed_name_status, first_match, included, load_json, parse_simple_manifest


ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"
ARCHIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "archive"
OWNERSHIP_POLICY = PROJECT_ROOT / ".ai" / "guards" / "file_ownership.yaml"
REPORT = PROJECT_ROOT / "target" / "ai_diff_ownership_report.json"
STATES = {"active_owned", "archived_owned", "unowned", "ambiguous", "out_of_scope", "approval_required"}


@dataclass(frozen=True)
class Owner:
    kind: str
    work_item_id: str
    contract: dict[str, Any]
    summary: dict[str, Any] | None


@dataclass(frozen=True)
class Ownership:
    path: str
    state: str
    owners: list[str]
    detail: str


def string_list(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def load_pair(contract_path: Path, kind: str) -> Owner | None:
    summary_path = Path(str(contract_path).replace(".contract.json", ".summary.json"))
    if not summary_path.is_file() and kind == "archived":
        return None
    try:
        contract = load_json(contract_path)
        summary = load_json(summary_path) if summary_path.is_file() else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    raw_work_item_id = contract.get("workItemId")
    work_item_id = raw_work_item_id if isinstance(raw_work_item_id, str) else contract_path.stem
    return Owner(kind, work_item_id, contract, summary)


def owners(*, base: str = "", active_contract: dict[str, Any] | None = None) -> list[Owner]:
    result: list[Owner] = []
    if isinstance(active_contract, dict):
        raw_work_item_id = active_contract.get("workItemId")
        work_item_id = raw_work_item_id if isinstance(raw_work_item_id, str) else "active"
        result.append(Owner("active", work_item_id, active_contract, None))
    elif not base:
        for path in sorted(ACTIVE_DIR.glob("*.contract.json")):
            owner = load_pair(path, "active")
            if owner:
                result.append(owner)
    if base:
        # PR Preview must use exactly the archive evidence set consumed by the
        # final authority.  Scanning every historical archive makes broad old
        # scopes create false ambiguity for a path that this PR already owns.
        from ai_check_pr import archived_contract_paths

        archive_paths = archived_contract_paths(base)
    else:
        archive_paths = sorted(ARCHIVE_DIR.rglob("*.contract.json"))
    for path in archive_paths:
        owner = load_pair(path, "archived")
        if owner:
            result.append(owner)
    return result


def covers(owner: Owner, path: str) -> tuple[bool, bool]:
    scoped = included(path, string_list(owner.contract.get("scope")))
    excluded = included(path, string_list(owner.contract.get("outOfScope")))
    if not scoped or excluded:
        return False, excluded
    if owner.kind == "archived" and (owner.summary is None or path not in changed_file_paths(owner.summary)):
        return False, False
    return True, False


def approved(owner: Owner) -> bool:
    approval = owner.contract.get("restrictedWriteApproval")
    return isinstance(approval, dict) and approval.get("approved") is True


def is_unchanged_active_baseline(owner: Owner, path: str) -> bool:
    """Return whether ``path`` predates an active Work Item unchanged.

    A broad new Contract must not silently claim a dirty file that existed when
    the task started.  If the file changed again, it is a task-era change and
    can be evaluated normally.
    """
    if owner.kind != "active":
        return False
    baseline = owner.contract.get("baselineDirtyPaths")
    if not isinstance(baseline, list):
        return False
    for item in baseline:
        if not isinstance(item, dict) or item.get("path") != path:
            continue
        # Import lazily to keep the public data model small and testable.
        from ai_common import path_fingerprint

        fingerprint = item.get("fingerprint")
        return isinstance(fingerprint, str) and path_fingerprint(path) == fingerprint
    return False


def classify(path: str, candidates: list[Owner], ownership: dict[str, dict[str, str]], *, pr_mode: bool = False) -> Ownership:
    covering: list[Owner] = []
    excluded: list[Owner] = []
    for owner in candidates:
        if is_unchanged_active_baseline(owner, path):
            continue
        covered, out = covers(owner, path)
        if covered:
            covering.append(owner)
        elif out:
            excluded.append(owner)
    # A current active Work Item is the authoritative owner for a path changed
    # after its baseline.  Archived evidence can still own an unchanged older
    # diff, but must not make a legitimate follow-up edit look ambiguous.
    active_covering = [owner for owner in covering if owner.kind == "active"]
    if len(active_covering) == 1:
        covering = active_covering
    labels = [f"{owner.kind}:{owner.work_item_id}" for owner in covering]
    if len(covering) > 1:
        if pr_mode and all(owner.kind == "archived" for owner in covering):
            effective = covering[-1]
            return Ownership(
                path,
                f"{effective.kind}_owned",
                labels,
                "covered by multiple effective archive Contract/Summary pairs; latest archive pair wins",
            )
        return Ownership(path, "ambiguous", labels, "multiple Work Items cover this path")
    if not covering:
        if excluded:
            return Ownership(path, "out_of_scope", [f"{o.kind}:{o.work_item_id}" for o in excluded], "covered by owner scope but excluded by outOfScope")
        return Ownership(path, "unowned", [], "no active or archived evidence covers this path")
    owner = covering[0]
    match = first_match(path, ownership)
    if match and match[1].get("aiWrite") == "forbidden":
        return Ownership(path, "unowned", labels, "forbidden ownership cannot be claimed")
    if match and match[1].get("aiWrite") == "restricted" and not approved(owner):
        extras = []
        if match[1].get("reviewFocus"):
            extras.append(f"review focus: {match[1]['reviewFocus']}")
        if match[1].get("requiredTests"):
            extras.append(f"required tests: {match[1]['requiredTests']}")
        detail = "restricted path requires contract.restrictedWriteApproval.approved"
        if extras:
            detail += "; " + "; ".join(extras)
        return Ownership(path, "approval_required", labels, detail)
    return Ownership(path, f"{owner.kind}_owned", labels, "covered by Contract scope" if owner.kind == "active" else "covered by Contract scope and Summary changedFiles")


def preview(*, base: str = "", contract: dict[str, Any] | None = None) -> list[Ownership]:
    explicit_base = bool(base)
    if not base and isinstance(contract, dict):
        contract_base = contract.get("baseCommit")
        if isinstance(contract_base, str) and contract_base:
            base = contract_base
    diff_contract = {"baseCommit": base, "baselineDirtyPaths": []} if explicit_base else contract
    try:
        changed = changed_name_status(diff_contract, ignore_baseline_dirty=explicit_base)
    except RuntimeError:
        if contract is None:
            raise
        base = ""
        diff_contract = {"baselineDirtyPaths": []}
        changed = changed_name_status(diff_contract, ignore_baseline_dirty=False)
    audit_paths: set[str] = set()
    if base:
        try:
            audit_paths = set(archive_evidence_changes(base))
        except RuntimeError:
            audit_paths = set()
    policy = parse_simple_manifest(OWNERSHIP_POLICY)
    candidates = owners(base=base, active_contract=contract)
    values: list[Ownership] = []
    for status, path in changed:
        if path in audit_paths:
            continue
        if path.startswith(".ai/work-items/archive/") and status != "A":
            values.append(Ownership(path, "unowned", [], "archived evidence is append-only; create new evidence instead of modifying it"))
        else:
            values.append(classify(path, candidates, policy, pr_mode=bool(base)))
    return sorted(values, key=lambda item: item.path)


def counts(values: list[Ownership]) -> dict[str, int]:
    return {state: sum(item.state == state for item in values) for state in sorted(STATES)}


def format_preview(values: list[Ownership]) -> list[str]:
    result = ["## Diff Ownership Preview"]
    summary = counts(values)
    result.append("- " + ", ".join(f"{state}: `{count}`" for state, count in summary.items()))
    if not values:
        result.append("- no changed paths")
    for item in values:
        result.append(f"- [{item.state}] `{item.path}` — {item.detail}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=os.environ.get("AI_BASE_COMMIT", ""))
    parser.add_argument("--contract")
    parser.add_argument("--json", action="store_true", help="Print JSON in addition to writing the report.")
    args = parser.parse_args()
    try:
        contract = load_json(Path(args.contract)) if args.contract else None
        values = preview(base=args.base, contract=contract)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"diff ownership preview failed: {exc}", file=sys.stderr)
        return 1
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "base": args.base or None,
        "counts": counts(values),
        "items": [asdict(item) for item in values],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n".join(format_preview(values)))
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    accepted = {"active_owned", "archived_owned"}
    return 0 if all(item.state in accepted for item in values) else 1


if __name__ == "__main__":
    raise SystemExit(main())
