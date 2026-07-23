#!/usr/bin/env python3
"""Generate release freeze metadata only after lifecycle closure and base sync."""

from __future__ import annotations

import json
import argparse
import sys

from ai_common import PROJECT_ROOT, discover_remote_default_candidates, run_git
from check_release_preflight import canonical_archive_sha, canonical_source_tree
from check_supply_chain import sha256_text


def _fail(message: str) -> int:
    print(f"release freeze finalization blocked: {message}", file=sys.stderr)
    return 1


def main(candidate_task: str | None = None) -> int:
    root = PROJECT_ROOT
    candidates = discover_remote_default_candidates(run_git)
    if len(candidates) != 1:
        return _fail("remote default branch is not uniquely discoverable")
    remote, branch = candidates[0]
    current = run_git(["branch", "--show-current"])
    current_branch = current.stdout.strip() if current.returncode == 0 else ""
    if candidate_task is None and current_branch != branch:
        return _fail(f"must run on synchronized default branch {branch}")
    if candidate_task is not None and (not current_branch or current_branch == branch):
        return _fail(f"candidate mode must run on a dedicated Work Item branch, not {branch}")
    status = run_git(["status", "--porcelain", "--untracked-files=all"])
    if status.returncode != 0 or status.stdout.strip():
        return _fail("worktree must be clean before freeze finalization")
    head = run_git(["rev-parse", "HEAD"])
    remote_head = run_git(["rev-parse", f"{remote}/{branch}"])
    if candidate_task is None and (
        head.returncode != 0
        or remote_head.returncode != 0
        or head.stdout.strip() != remote_head.stdout.strip()
    ):
        return _fail("local default branch must equal the remote default branch")
    active = sorted(
        path.name.removesuffix(".contract.json")
        for path in (root / ".ai" / "work-items" / "active").glob("*.contract.json")
    )
    if candidate_task is None and active:
        return _fail(f"active Work Items remain: {', '.join(active)}")
    if candidate_task is not None and active != [candidate_task]:
        return _fail(
            f"candidate mode requires exactly the active Work Item {candidate_task!r}; "
            f"found {active or 'none'}"
        )
    status_path = root / ".ai" / "cockpit" / "current_status.md"
    if candidate_task is None and "- State: `no_active_work_item`" not in status_path.read_text(
        encoding="utf-8"
    ):
        return _fail("Cockpit Status is not no_active_work_item")

    source_commit = head.stdout.strip()
    source_tree = canonical_source_tree(root, source_commit)
    archive_sha = canonical_archive_sha(root, source_commit)
    freeze_path = root / ".ai" / "cockpit" / "release-freeze.json"
    release_digests_path = root / ".ai" / "cockpit" / "release-digests.json"
    release_path = root / "release.json"
    release_state_path = root / "release-state.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    release_digests = json.loads(release_digests_path.read_text(encoding="utf-8"))
    release = json.loads(release_path.read_text(encoding="utf-8"))
    try:
        release_state = json.loads(release_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(f"release-state.json is missing or invalid: {exc}")
    if not isinstance(release_state, dict):
        return _fail("release-state.json must contain an object")
    metadata_digests = release_state.get("metadataDigests")
    if not isinstance(metadata_digests, dict):
        return _fail("release-state.json metadataDigests must contain an object")
    freeze.update(
        {
            "state": "frozen",
            "sourceTree": source_tree,
            "archiveSha256": archive_sha,
            "lifecycle": {
                "state": "closed_and_synchronized"
                if candidate_task is None
                else "candidate_prepared",
                "command": "make ai-close-work-item"
                if candidate_task is None
                else f"make finalize-release-freeze-candidate CANDIDATE_TASK={candidate_task}",
                "defaultBranch": branch,
                **({"candidateBranch": current_branch} if candidate_task is not None else {}),
                "baseCommit": source_tree,
                "worktreeClean": True,
            },
        }
    )
    release.setdefault("releaseArchive", {})["sha256"] = archive_sha
    freeze_path.write_text(
        json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    release_path.write_text(
        json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    metadata_digests["published"] = sha256_text(release_path.read_text(encoding="utf-8"))
    release_state_path.write_text(
        json.dumps(release_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # The manifest is committed after this command runs.  Persisting the
    # symbolic ref keeps it valid when that metadata commit changes HEAD;
    # preflight resolves it and still compares canonical commit identities.
    release_digests["sourceCommit"] = "HEAD"
    release_digests["releaseTag"] = release.get("releaseTag")
    release_digests.setdefault("artifacts", {})["release.json"] = sha256_text(
        release_path.read_text(encoding="utf-8")
    )
    release_digests_path.write_text(
        json.dumps(release_digests, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"release freeze finalized: source={source_commit} archive={archive_sha}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-task", default=None)
    args = parser.parse_args()
    raise SystemExit(main(candidate_task=args.candidate_task))
