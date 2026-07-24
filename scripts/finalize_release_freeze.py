#!/usr/bin/env python3
"""Generate release freeze metadata only after lifecycle closure and base sync."""

from __future__ import annotations

import json
import argparse
import sys

from ai_common import PROJECT_ROOT, discover_remote_default_candidates, included, run_git
from release_archive import canonical_archive_sha, canonical_source_tree
from check_supply_chain import sha256_text


def _fail(message: str) -> int:
    print(f"release freeze finalization blocked: {message}", file=sys.stderr)
    return 1


def main(
    candidate_task: str | None = None,
    premerge_task: str | None = None,
    source_commit: str | None = None,
    tag_target: str | None = None,
    metadata_commit: str | None = None,
) -> int:
    if candidate_task is not None and premerge_task is not None:
        return _fail("candidate and pre-merge modes are mutually exclusive")
    root = PROJECT_ROOT
    candidates = discover_remote_default_candidates(run_git)
    if len(candidates) != 1:
        return _fail("remote default branch is not uniquely discoverable")
    remote, branch = candidates[0]
    current = run_git(["branch", "--show-current"])
    current_branch = current.stdout.strip() if current.returncode == 0 else ""
    if candidate_task is None and premerge_task is None and current_branch != branch:
        return _fail(f"must run on synchronized default branch {branch}")
    if (candidate_task is not None or premerge_task is not None) and (
        not current_branch or current_branch == branch
    ):
        return _fail(f"candidate mode must run on a dedicated Work Item branch, not {branch}")
    status = run_git(["status", "--porcelain", "--untracked-files=all"])
    if status.returncode != 0 or status.stdout.strip():
        return _fail("worktree must be clean before freeze finalization")
    head = run_git(["rev-parse", "HEAD"])
    remote_head = run_git(["rev-parse", f"{remote}/{branch}"])
    if (
        candidate_task is None
        and premerge_task is None
        and (
            head.returncode != 0
            or remote_head.returncode != 0
            or head.stdout.strip() != remote_head.stdout.strip()
        )
    ):
        return _fail("local default branch must equal the remote default branch")
    active = sorted(
        path.name.removesuffix(".contract.json")
        for path in (root / ".ai" / "work-items" / "active").glob("*.contract.json")
    )
    if candidate_task is None and premerge_task is None and active:
        return _fail(f"active Work Items remain: {', '.join(active)}")
    if candidate_task is not None and active != [candidate_task]:
        return _fail(
            f"candidate mode requires exactly the active Work Item {candidate_task!r}; "
            f"found {active or 'none'}"
        )
    if premerge_task is not None:
        archived_contract = (
            root / ".ai" / "work-items" / "archive" / "2026" / f"{premerge_task}.contract.json"
        )
        if active:
            return _fail(
                f"pre-merge finalization requires no active Work Items; found {', '.join(active)}"
            )
        if not archived_contract.exists():
            return _fail(
                f"pre-merge finalization requires archived Work Item evidence: {premerge_task}"
            )
    if candidate_task is not None or premerge_task is not None:
        contract_path = (
            root / ".ai" / "work-items" / "active" / f"{candidate_task}.contract.json"
            if candidate_task is not None
            else root / ".ai" / "work-items" / "archive" / "2026" / f"{premerge_task}.contract.json"
        )
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return _fail(f"release metadata ownership Contract is missing or invalid: {exc}")
        generated_paths = [
            "release.json",
            "release-state.json",
            ".ai/cockpit/release-freeze.json",
            ".ai/cockpit/release-digests.json",
        ]
        scope = [pattern for pattern in contract.get("scope", []) if isinstance(pattern, str)]
        out_of_scope = [
            pattern for pattern in contract.get("outOfScope", []) if isinstance(pattern, str)
        ]
        missing = [
            path
            for path in generated_paths
            if not included(path, scope) or included(path, out_of_scope)
        ]
        if missing:
            return _fail(
                "release metadata generation paths are not fully covered by the Work Item "
                f"Contract scope: {', '.join(missing)}"
            )
    status_path = root / ".ai" / "cockpit" / "current_status.md"
    if candidate_task is None and "- State: `no_active_work_item`" not in status_path.read_text(
        encoding="utf-8"
    ):
        return _fail("Cockpit Status is not no_active_work_item")

    resolved_head = head.stdout.strip()
    source_identity = source_commit or resolved_head
    tag_identity = tag_target or source_identity
    metadata_identity = metadata_commit or source_identity
    if premerge_task is not None:
        resolved_source = run_git(["rev-parse", source_identity])
        if resolved_source.returncode != 0 or not resolved_source.stdout.strip():
            return _fail(f"source identity cannot be resolved: {source_identity}")
    # The controlled source identity remains a future default-branch ref for
    # post-merge resolution. Canonical content is materialized from this clean
    # candidate HEAD; export-ignored metadata and Work Item evidence let a clean
    # merge preserve those bytes while changing commit identity.
    materialization_commit = resolved_head if premerge_task is not None else source_identity
    source_tree = canonical_source_tree(root, materialization_commit)
    archive_sha = canonical_archive_sha(root, materialization_commit)
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
            "sourceCommit": source_identity,
            "tagTarget": tag_identity,
            "metadataCommit": metadata_identity,
            "releaseTag": release.get("releaseTag"),
            "sourceTree": source_tree,
            "archiveSha256": archive_sha,
            "lifecycle": {
                "state": (
                    "closed_and_synchronized"
                    if candidate_task is None and premerge_task is None
                    else "candidate_prepared"
                    if candidate_task is not None
                    else "premerge_finalized"
                ),
                "command": (
                    "make ai-close-work-item"
                    if candidate_task is None and premerge_task is None
                    else f"make finalize-release-freeze-candidate CANDIDATE_TASK={candidate_task}"
                    if candidate_task is not None
                    else f"make finalize-release-freeze-premerge TASK={premerge_task}"
                ),
                "defaultBranch": branch,
                **(
                    {"candidateBranch": current_branch}
                    if candidate_task is not None
                    else {"premergeWorkItem": premerge_task}
                    if premerge_task is not None
                    else {}
                ),
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
    release_digests["sourceCommit"] = source_identity
    release_digests["tagTarget"] = tag_identity
    release_digests["metadataCommit"] = metadata_identity
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
    parser.add_argument("--premerge-task", default=None)
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--tag-target", default=None)
    parser.add_argument("--metadata-commit", default=None)
    args = parser.parse_args()
    raise SystemExit(
        main(
            candidate_task=args.candidate_task,
            premerge_task=args.premerge_task,
            source_commit=args.source_commit,
            tag_target=args.tag_target,
            metadata_commit=args.metadata_commit,
        )
    )
