#!/usr/bin/env python3
"""Archive a Work Item from active/ to archive/YYYY/."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ai_common import PROJECT_ROOT, load_json, redact_machine_paths_in_data, save_json
from ai_observability import AiEvent, AiEventLevel, AiEventType, create_observability


ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"
ARCHIVE_BASE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "archive"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive a Work Item.")
    parser.add_argument("contract", help="Path to the active contract JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract_path = Path(args.contract).resolve()

    try:
        contract_path.relative_to(ACTIVE_DIR)
    except ValueError:
        print(f"ERROR: Contract must be in {ACTIVE_DIR.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        return 1

    if not contract_path.exists():
        print(f"ERROR: Contract not found: {contract_path.relative_to(PROJECT_ROOT)}", file=sys.stderr)
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

    if mode == "code" and not summary_path.exists():
        print(f"ERROR: mode code requires Summary: {summary_path.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        return 1

    target_dir = ARCHIVE_BASE_DIR / str(datetime.now().year)
    files_to_move: list[tuple[Path, Path]] = [(contract_path, target_dir / contract_path.name)]
    if summary_path.exists():
        files_to_move.append((summary_path, target_dir / summary_path.name))
    if review_path.exists():
        files_to_move.append((review_path, target_dir / review_path.name))

    for _, target in files_to_move:
        if target.exists():
            print(f"ERROR: Target already exists: {target.relative_to(PROJECT_ROOT)}", file=sys.stderr)
            return 1

    if args.dry_run:
        print("Dry run: files that would be archived:")
        for src, target in files_to_move:
            print(f"  {src.relative_to(PROJECT_ROOT)} -> {target.relative_to(PROJECT_ROOT)}")
        return 0

    target_dir.mkdir(parents=True, exist_ok=True)
    if summary_path.exists():
        summary = redact_machine_paths_in_data(load_json(summary_path))
        summary["contractPath"] = (target_dir / contract_path.name).relative_to(PROJECT_ROOT).as_posix()
        changed = summary.get("changedFiles", [])
        if isinstance(changed, list):
            replacements = {
                contract_path.relative_to(PROJECT_ROOT).as_posix(): (target_dir / contract_path.name).relative_to(PROJECT_ROOT).as_posix(),
                summary_path.relative_to(PROJECT_ROOT).as_posix(): (target_dir / summary_path.name).relative_to(PROJECT_ROOT).as_posix(),
            }
            for item in changed:
                if isinstance(item, dict) and item.get("path") in replacements:
                    item["path"] = replacements[item["path"]]
            existing = {item.get("path") for item in changed if isinstance(item, dict)}
            for archived_path in replacements.values():
                if archived_path not in existing:
                    changed.append({"path": archived_path, "reason": "Archived Work Item audit evidence."})
        save_json(summary_path, summary)

    for src, target in files_to_move:
        shutil.move(str(src), str(target))
        print(f"moved: {target.relative_to(PROJECT_ROOT)}")

    obs = create_observability(work_item_id=work_item_id)
    obs.record(AiEvent(AiEventType.CHECK_PASSED, AiEventLevel.INFO, f"Work Item archived to {target_dir.name}", check_id="aiArchive", fields={"year": target_dir.name, "files": len(files_to_move)}))
    subprocess.run([sys.executable, "scripts/ai_generate_status.py", "--no-active"], cwd=PROJECT_ROOT, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
