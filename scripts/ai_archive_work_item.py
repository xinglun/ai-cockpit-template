#!/usr/bin/env python3
"""Archive a Work Item from active/ to archive/YYYY/."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ai_check_summary import validate_summary
from ai_check_work_item import validate_contract
from ai_common import (
    PROJECT_ROOT,
    changed_paths,
    load_json,
    non_empty_string,
    path_fingerprint,
    redact_machine_paths_in_data,
    save_json,
    verification_key,
)
from ai_observability import AiEvent, AiEventLevel, AiEventType, create_observability


ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"
ARCHIVE_BASE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "archive"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive a Work Item.")
    parser.add_argument("contract", help="Path to the active contract JSON.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print actions without modifying files."
    )
    return parser.parse_args()


def _restore_files(files_to_move: list[tuple[Path, Path]]) -> None:
    for src, target in reversed(files_to_move):
        if target.exists():
            shutil.move(str(target), str(src))


def _generate_status(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _worktree_digest(paths: list[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path_fingerprint(path).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _summary_worktree_digest(summary: dict[str, object]) -> str:
    verification = summary.get("verification", [])
    if not isinstance(verification, list):
        return ""
    for item in reversed(verification):
        if not isinstance(item, dict):
            continue
        if verification_key(item) != "aiSummary" or item.get("result") != "passed":
            continue
        digest = item.get("worktreeDigest")
        if non_empty_string(digest):
            return str(digest)
    return ""


def _current_worktree_digest(contract: dict[str, object]) -> str:
    return _worktree_digest(changed_paths(contract))


def _validate_archive_inputs(
    contract_path: Path, contract: dict, summary_path: Path | None, summary: dict | None
) -> list[str]:
    issues = validate_contract(contract)
    if summary_path is None or summary is None:
        return issues
    contract_rel = contract_path.relative_to(PROJECT_ROOT).as_posix()
    summary_rel = summary_path.relative_to(PROJECT_ROOT).as_posix()
    contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    issues.extend(
        validate_summary(
            summary,
            contract,
            expected_contract_hash=contract_hash,
            contract_path=contract_rel,
            summary_path=summary_rel,
        )
    )
    return issues


def main() -> int:
    args = parse_args()
    contract_path = Path(args.contract).resolve()

    try:
        contract_path.relative_to(ACTIVE_DIR)
    except ValueError:
        print(f"ERROR: Contract must be in {ACTIVE_DIR.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        return 1

    if not contract_path.exists():
        print(
            f"ERROR: Contract not found: {contract_path.relative_to(PROJECT_ROOT)}", file=sys.stderr
        )
        return 1

    try:
        contract = load_json(contract_path)
    except Exception as exc:
        print(f"ERROR: Failed to read contract: {exc}", file=sys.stderr)
        return 1

    work_item_id = contract.get("workItemId")
    if not work_item_id:
        print("ERROR: Contract missing workItemId", file=sys.stderr)
        return 1

    file_basename = contract_path.name.replace(".contract.json", "")
    mode = contract.get("mode")
    summary_path = ACTIVE_DIR / f"{file_basename}.summary.json"
    review_path = ACTIVE_DIR / f"{file_basename}.review.json"
    has_summary = summary_path.exists()
    has_review = review_path.exists()

    if mode == "code" and not has_summary:
        print(
            f"ERROR: mode code requires Summary: {summary_path.relative_to(PROJECT_ROOT)}",
            file=sys.stderr,
        )
        return 1

    summary = None
    if has_summary:
        try:
            summary = load_json(summary_path)
        except Exception as exc:
            print(f"ERROR: Failed to read summary: {exc}", file=sys.stderr)
            return 1

    issues = _validate_archive_inputs(
        contract_path, contract, summary_path if has_summary else None, summary
    )
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1

    if has_summary:
        recorded_digest = _summary_worktree_digest(summary or {})
        current_digest = _current_worktree_digest(contract)
        if recorded_digest and recorded_digest != current_digest:
            print(
                "ERROR: Summary worktreeDigest does not match current Work Item state; re-run ai-finish before archiving.",
                file=sys.stderr,
            )
            return 1

    target_dir = ARCHIVE_BASE_DIR / str(datetime.now().year)
    files_to_move: list[tuple[Path, Path]] = [(contract_path, target_dir / contract_path.name)]
    if has_summary:
        files_to_move.append((summary_path, target_dir / summary_path.name))
    if has_review:
        files_to_move.append((review_path, target_dir / review_path.name))
    summary_tmp = target_dir / f"{summary_path.name}.tmp" if has_summary else None

    for _, target in files_to_move:
        if target.exists():
            print(
                f"ERROR: Target already exists: {target.relative_to(PROJECT_ROOT)}", file=sys.stderr
            )
            return 1

    if args.dry_run:
        print("Dry run: files that would be archived:")
        for src, target in files_to_move:
            print(f"  {src.relative_to(PROJECT_ROOT)} -> {target.relative_to(PROJECT_ROOT)}")
        return 0

    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        for src, target in files_to_move:
            shutil.move(str(src), str(target))
            print(f"moved: {target.relative_to(PROJECT_ROOT)}")
        _generate_status([sys.executable, "scripts/ai_generate_status.py", "--no-active"])

        if has_summary:
            archived_contract = (
                (target_dir / contract_path.name).relative_to(PROJECT_ROOT).as_posix()
            )
            archived_summary = (target_dir / summary_path.name).relative_to(PROJECT_ROOT).as_posix()
            replacements = {
                contract_path.relative_to(PROJECT_ROOT).as_posix(): archived_contract,
                summary_path.relative_to(PROJECT_ROOT).as_posix(): archived_summary,
            }
            if has_review:
                replacements[review_path.relative_to(PROJECT_ROOT).as_posix()] = (
                    (target_dir / review_path.name).relative_to(PROJECT_ROOT).as_posix()
                )
            summary = redact_machine_paths_in_data(load_json(target_dir / summary_path.name))
            summary["contractPath"] = archived_contract
            changed = summary.get("changedFiles", [])
            if isinstance(changed, list):
                for item in changed:
                    if isinstance(item, dict) and item.get("path") in replacements:
                        item["path"] = replacements[item["path"]]
                existing = {item.get("path") for item in changed if isinstance(item, dict)}
                for archived_path in replacements.values():
                    if archived_path not in existing:
                        changed.append(
                            {"path": archived_path, "reason": "Archived Work Item audit evidence."}
                        )
            summary_target = target_dir / summary_path.name
            assert summary_tmp is not None
            save_json(summary_tmp, summary)
            summary_tmp.replace(summary_target)
    except Exception as exc:
        if summary_tmp and summary_tmp.exists():
            summary_tmp.unlink()
        try:
            _restore_files(files_to_move)
        except Exception as rollback_exc:
            print(f"ERROR: Failed to roll back archive files: {rollback_exc}", file=sys.stderr)
        try:
            subprocess.run(
                [
                    sys.executable,
                    "scripts/ai_generate_status.py",
                    str(contract_path),
                    "--summary",
                    str(summary_path),
                ],
                cwd=PROJECT_ROOT,
                check=False,
            )
        except Exception:
            pass
        print(f"ERROR: Failed to archive Work Item: {exc}", file=sys.stderr)
        return 1

    obs = create_observability(work_item_id=work_item_id)
    obs.record(
        AiEvent(
            AiEventType.CHECK_PASSED,
            AiEventLevel.INFO,
            f"Work Item archived to {target_dir.name}",
            check_id="aiArchive",
            fields={"year": target_dir.name, "files": len(files_to_move)},
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
