#!/usr/bin/env python3
"""Archive a Work Item from active/ to archive/YYYY/."""

from __future__ import annotations

import argparse
import fnmatch
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
    clean_git_environment,
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


def owned_success_criteria_path(contract_path: Path) -> Path:
    """Return the task-owned Success Criteria sibling for an active Contract."""
    return contract_path.with_name(contract_path.name.replace(".contract.json", ".success.json"))


def _archive_index_path() -> Path:
    return ARCHIVE_BASE_DIR / "index.json"


def _is_ignored(path: Path) -> bool:
    """Identify local-only archive evidence excluded from repository checkouts."""
    try:
        relative_path = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return False
    gitignore = PROJECT_ROOT / ".gitignore"
    if not gitignore.is_file():
        return False
    relative_text = relative_path.as_posix()
    ignored = False
    for line in gitignore.read_text(encoding="utf-8").splitlines():
        pattern = line.strip()
        if not pattern or pattern.startswith("#"):
            continue
        negated = pattern.startswith("!")
        if negated:
            pattern = pattern[1:]
        pattern = pattern.rstrip("/").lstrip("/")
        if fnmatch.fnmatch(relative_text, pattern) or fnmatch.fnmatch(path.name, pattern):
            ignored = not negated
    return ignored


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive a Work Item.")
    parser.add_argument("contract", nargs="?", help="Path to the active contract JSON.")
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild the archive discovery index from authoritative Contract/Summary pairs.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print actions without modifying files."
    )
    return parser.parse_args()


def _restore_files(files_to_move: list[tuple[Path, Path]]) -> None:
    for src, target in reversed(files_to_move):
        if target.exists():
            shutil.move(str(target), str(src))


def _generate_status(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, env=clean_git_environment(), check=True)


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
    summary_path = str(contract.get("summaryPath", ""))
    paths = [path for path in changed_paths(contract) if path != summary_path]
    return _worktree_digest(paths)


def _next_archive_sequence() -> int:
    """Return the next monotonic sequence, preferring the archive index."""
    highest = 0
    try:
        index = load_json(_archive_index_path())
    except (OSError, ValueError):
        index = None
    if isinstance(index, dict) and isinstance(index.get("entries"), list):
        for entry in index["entries"]:
            if isinstance(entry, dict) and isinstance(entry.get("archiveSequence"), int):
                highest = max(highest, int(entry["archiveSequence"]))
        if highest:
            return highest + 1
    for summary_path in ARCHIVE_BASE_DIR.rglob("*.summary.json"):
        try:
            summary = load_json(summary_path)
        except (OSError, ValueError):
            continue
        value = summary.get("archiveSequence")
        if isinstance(value, int) and not isinstance(value, bool):
            highest = max(highest, value)
    return highest + 1


def _archive_entry(
    *,
    contract_path: Path,
    summary_path: Path | None,
    target_dir: Path,
    archive_sequence: int,
) -> dict[str, object]:
    """Build a portable discovery record for one archived Work Item."""
    contract_target = target_dir / contract_path.name
    contract = load_json(contract_target)
    entry: dict[str, object] = {
        "workItemId": contract.get("workItemId", contract_path.stem.replace(".contract", "")),
        "archiveSequence": archive_sequence,
        "archiveYear": target_dir.name,
        "contractPath": contract_target.relative_to(PROJECT_ROOT).as_posix(),
        "contractSha256": hashlib.sha256(contract_target.read_bytes()).hexdigest(),
        "archivedAt": datetime.now().astimezone().isoformat(),
    }
    if summary_path is not None:
        summary_target = target_dir / summary_path.name
        entry["summaryPath"] = summary_target.relative_to(PROJECT_ROOT).as_posix()
        entry["summarySha256"] = hashlib.sha256(summary_target.read_bytes()).hexdigest()
    manifest_target = target_dir / contract_path.name.replace(
        ".contract.json", ".archive-manifest.json"
    )
    if manifest_target.is_file():
        entry["manifestPath"] = manifest_target.relative_to(PROJECT_ROOT).as_posix()
        entry["manifestSha256"] = hashlib.sha256(manifest_target.read_bytes()).hexdigest()
    return entry


def _archive_manifest(
    *, contract_target: Path, summary_target: Path, archive_sequence: int
) -> dict[str, object]:
    """Build the immutable root after Contract and Summary are frozen."""
    return {
        "format": "ai-cockpit-archive-manifest",
        "manifestVersion": 1,
        "workItemId": load_json(contract_target).get("workItemId"),
        "archiveSequence": archive_sequence,
        "contractPath": contract_target.relative_to(PROJECT_ROOT).as_posix(),
        "summaryPath": summary_target.relative_to(PROJECT_ROOT).as_posix(),
        "contractSha256": hashlib.sha256(contract_target.read_bytes()).hexdigest(),
        "summarySha256": hashlib.sha256(summary_target.read_bytes()).hexdigest(),
        "generatedStatusExcluded": True,
    }


def _archive_sequence_key(item: object) -> int:
    if isinstance(item, dict) and isinstance(item.get("archiveSequence"), int):
        return int(item["archiveSequence"])
    return 0


def _load_archive_index() -> dict[str, object]:
    """Load the index and add any authoritative archive pair it omits."""
    try:
        index = load_json(_archive_index_path())
    except (OSError, ValueError):
        index = None
    if isinstance(index, dict) and isinstance(index.get("entries"), list):
        entries = index["entries"]
    else:
        entries = []
        index = {
            "indexVersion": 1,
            "description": "Discovery index; archived Contract and Summary files remain authoritative.",
            "entries": entries,
        }

    deduplicated: list[dict[str, object]] = []
    positions: dict[tuple[object, object], int] = {}
    for existing_entry in entries:
        if not isinstance(existing_entry, dict):
            continue
        pair = (existing_entry.get("contractPath"), existing_entry.get("summaryPath"))
        position = positions.get(pair)
        if position is None:
            positions[pair] = len(deduplicated)
            deduplicated.append(existing_entry)
            continue
        current = deduplicated[position]
        current_is_strict = isinstance(current.get("contractSha256"), str) and isinstance(
            current.get("summarySha256"), str
        )
        candidate_is_strict = isinstance(existing_entry.get("contractSha256"), str) and isinstance(
            existing_entry.get("summarySha256"), str
        )
        if (not current_is_strict and candidate_is_strict) or (
            current.get("archivedAt") == "legacy" and existing_entry.get("archivedAt") != "legacy"
        ):
            deduplicated[position] = existing_entry
    entries = [
        entry
        for entry in deduplicated
        if isinstance(entry.get("contractPath"), str)
        and isinstance(entry.get("summaryPath"), str)
        and (PROJECT_ROOT / str(entry["contractPath"])).is_file()
        and (PROJECT_ROOT / str(entry["summaryPath"])).is_file()
        and not _is_ignored(PROJECT_ROOT / str(entry["contractPath"]))
        and not _is_ignored(PROJECT_ROOT / str(entry["summaryPath"]))
    ]
    index["entries"] = entries

    indexed_pairs = {
        (entry.get("contractPath"), entry.get("summaryPath"))
        for entry in entries
        if isinstance(entry, dict)
    }
    for summary_path in ARCHIVE_BASE_DIR.rglob("*.summary.json"):
        if _is_ignored(summary_path):
            continue
        try:
            summary = load_json(summary_path)
            contract_path = PROJECT_ROOT / str(summary["contractPath"])
            if not contract_path.exists():
                contract_path = summary_path.with_name(
                    summary_path.name.replace(".summary.json", ".contract.json")
                )
            sequence = summary.get("archiveSequence")
            if not contract_path.exists() or not isinstance(summary.get("workItemId"), str):
                continue
            if _is_ignored(contract_path):
                continue
            contract_rel = contract_path.relative_to(PROJECT_ROOT).as_posix()
            summary_rel = summary_path.relative_to(PROJECT_ROOT).as_posix()
            if (contract_rel, summary_rel) in indexed_pairs:
                continue
            entry: dict[str, object] = {
                "workItemId": summary["workItemId"],
                "archiveSequence": sequence if isinstance(sequence, int) else 0,
                "archiveYear": summary_path.parent.name,
                "contractPath": contract_rel,
                "summaryPath": summary_rel,
                "archivedAt": summary.get("archivedAt", "legacy"),
            }
            if isinstance(sequence, int) and sequence > 0:
                entry["contractSha256"] = hashlib.sha256(contract_path.read_bytes()).hexdigest()
                entry["summarySha256"] = hashlib.sha256(summary_path.read_bytes()).hexdigest()
            entries.append(entry)
            indexed_pairs.add((contract_rel, summary_rel))
        except (KeyError, OSError, ValueError):
            continue
    entries.sort(key=_archive_sequence_key)
    return index


def _write_archive_index(index: dict[str, object]) -> None:
    """Atomically persist the discovery index."""
    ARCHIVE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    index_path = _archive_index_path()
    temporary = index_path.with_suffix(".json.tmp")
    save_json(temporary, index)
    temporary.replace(index_path)


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
    if getattr(args, "rebuild_index", False):
        try:
            index = _load_archive_index()
            _write_archive_index(index)
        except (OSError, ValueError, KeyError) as exc:
            print(f"ERROR: Failed to rebuild archive index: {exc}", file=sys.stderr)
            return 1
        entries = index.get("entries", [])
        count = len(entries) if isinstance(entries, list) else 0
        print(f"archive index rebuilt: {count} entries")
        return 0
    if not args.contract:
        print(
            "ERROR: an active Contract path is required unless --rebuild-index is used",
            file=sys.stderr,
        )
        return 1
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
    success_path = owned_success_criteria_path(contract_path)
    has_summary = summary_path.exists()
    has_review = review_path.exists()
    has_success = success_path.exists()

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
        digest_contract = dict(contract)
        digest_contract["summaryPath"] = summary_path.relative_to(PROJECT_ROOT).as_posix()
        current_digest = _current_worktree_digest(digest_contract)
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
    if has_success:
        files_to_move.append((success_path, target_dir / success_path.name))
    summary_tmp = target_dir / f"{summary_path.name}.tmp" if has_summary else None
    manifest_target = target_dir / contract_path.name.replace(
        ".contract.json", ".archive-manifest.json"
    )

    for _, target in files_to_move:
        if target.exists():
            print(
                f"ERROR: Target already exists: {target.relative_to(PROJECT_ROOT)}", file=sys.stderr
            )
            return 1
    if manifest_target.exists():
        print(
            f"ERROR: Target already exists: {manifest_target.relative_to(PROJECT_ROOT)}",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print("Dry run: files that would be archived:")
        for src, target in files_to_move:
            print(f"  {src.relative_to(PROJECT_ROOT)} -> {target.relative_to(PROJECT_ROOT)}")
        return 0

    archive_sequence = _next_archive_sequence()
    target_dir.mkdir(parents=True, exist_ok=True)
    index_path = _archive_index_path()
    index_backup = index_path.read_bytes() if index_path.exists() else None
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
            if has_success:
                replacements[success_path.relative_to(PROJECT_ROOT).as_posix()] = (
                    (target_dir / success_path.name).relative_to(PROJECT_ROOT).as_posix()
                )
            summary = redact_machine_paths_in_data(load_json(target_dir / summary_path.name))
            summary["contractPath"] = archived_contract
            summary["archiveSequence"] = archive_sequence
            changed = summary.get("changedFiles", [])
            if isinstance(changed, list):
                if not any(
                    isinstance(item, dict) and item.get("path") == ".ai/cockpit/current_status.md"
                    for item in changed
                ):
                    changed.append(
                        {
                            "path": ".ai/cockpit/current_status.md",
                            "reason": "Generated no-active cockpit status after archival.",
                        }
                    )
                for item in changed:
                    if isinstance(item, dict) and item.get("path") in replacements:
                        item["path"] = replacements[item["path"]]
                existing = {item.get("path") for item in changed if isinstance(item, dict)}
                for archived_path in replacements.values():
                    if archived_path not in existing:
                        changed.append(
                            {"path": archived_path, "reason": "Archived Work Item audit evidence."}
                        )
                index_rel = _archive_index_path().relative_to(PROJECT_ROOT).as_posix()
                if index_rel not in existing:
                    changed.append(
                        {
                            "path": index_rel,
                            "reason": "Generated archive discovery index.",
                        }
                    )
                manifest_rel = manifest_target.relative_to(PROJECT_ROOT).as_posix()
                if manifest_rel not in existing:
                    changed.append(
                        {"path": manifest_rel, "reason": "Immutable archive evidence root."}
                    )
            summary_target = target_dir / summary_path.name
            assert summary_tmp is not None
            save_json(summary_tmp, summary)
            summary_tmp.replace(summary_target)

            save_json(
                manifest_target,
                _archive_manifest(
                    contract_target=target_dir / contract_path.name,
                    summary_target=summary_target,
                    archive_sequence=archive_sequence,
                ),
            )

        index = _load_archive_index()
        entries = index.get("entries")
        if not isinstance(entries, list):
            raise ValueError("archive index entries must be a list")
        new_entry = _archive_entry(
            contract_path=contract_path,
            summary_path=summary_path if has_summary else None,
            target_dir=target_dir,
            archive_sequence=archive_sequence,
        )
        new_pair = (new_entry.get("contractPath"), new_entry.get("summaryPath"))
        for entry_index, entry in enumerate(entries):
            if (
                isinstance(entry, dict)
                and (entry.get("contractPath"), entry.get("summaryPath")) == new_pair
            ):
                entries[entry_index] = new_entry
                break
        else:
            entries.append(new_entry)
        entries.sort(key=_archive_sequence_key)
        _write_archive_index(index)
    except Exception as exc:
        if summary_tmp and summary_tmp.exists():
            summary_tmp.unlink()
        manifest_target.unlink(missing_ok=True)
        if index_backup is None:
            index_path.unlink(missing_ok=True)
        else:
            index_path.write_bytes(index_backup)
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
