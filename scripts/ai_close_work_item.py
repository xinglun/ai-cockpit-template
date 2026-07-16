#!/usr/bin/env python3
"""Close a completed Work Item by restoring a clean, synchronized repository."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from ai_check_summary import validate_summary
from ai_check_work_item import validate_contract
from ai_common import PROJECT_ROOT, clean_git_environment, load_json, run_git


ARCHIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "archive"
ACTIVE_DIR = PROJECT_ROOT / ".ai" / "work-items" / "active"
STATUS_PATH = PROJECT_ROOT / ".ai" / "cockpit" / "current_status.md"


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[[Sequence[str], bool], CommandResult]


def _run_git(args: Sequence[str], check: bool = False) -> CommandResult:
    result = run_git(list(args))
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _run_external(args: Sequence[str], check: bool = False) -> CommandResult:
    executable = shutil.which(args[0])
    if executable is None:
        raise RuntimeError(f"required command is unavailable: {args[0]}")
    result = subprocess.run(
        [executable, *args[1:]],
        cwd=PROJECT_ROOT,
        env=clean_git_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"{' '.join(args)} failed")
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _default_runner(args: Sequence[str], check: bool = False) -> CommandResult:
    if args and args[0] == "gh":
        return _run_external(args, check)
    return _run_git(args, check)


def _find_archived_contract(task: str) -> Path:
    matches = sorted(ARCHIVE_DIR.glob(f"*/{task}.contract.json"))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one archived Contract for {task}, found {len(matches)}"
        )
    return matches[0]


def _verify_archived_evidence(task: str) -> Path:
    if list(ACTIVE_DIR.glob("*.contract.json")) or list(ACTIVE_DIR.glob("*.summary.json")):
        raise RuntimeError("active Work Item evidence remains; archive the Work Item first")
    contract_path = _find_archived_contract(task)
    summary_path = contract_path.with_name(
        contract_path.name.replace(".contract.json", ".summary.json")
    )
    if not summary_path.is_file():
        raise RuntimeError(f"archived Summary is missing: {summary_path.relative_to(PROJECT_ROOT)}")
    contract = load_json(contract_path)
    summary = load_json(summary_path)
    issues = validate_contract(contract)
    issues.extend(
        validate_summary(
            summary,
            contract,
            contract_path=contract_path.relative_to(PROJECT_ROOT).as_posix(),
            summary_path=summary_path.relative_to(PROJECT_ROOT).as_posix(),
            legacy_archive=True,
        )
    )
    if issues:
        raise RuntimeError("archived Work Item evidence is invalid: " + "; ".join(issues))
    if "- State: `no_active_work_item`" not in STATUS_PATH.read_text(encoding="utf-8"):
        raise RuntimeError("Cockpit Status is not no_active_work_item")
    return contract_path


def _discover_base(runner: Runner) -> tuple[str, str]:
    remotes = runner(["remote"], False)
    if remotes.returncode != 0:
        raise RuntimeError("cannot enumerate Git remotes")
    candidates: list[tuple[str, str]] = []
    for remote in remotes.stdout.splitlines():
        remote = remote.strip()
        if not remote:
            continue
        head = runner(["symbolic-ref", "--quiet", "--short", f"refs/remotes/{remote}/HEAD"], False)
        if head.returncode == 0:
            ref = head.stdout.strip()
            prefix = f"{remote}/"
            if ref.startswith(prefix) and ref[len(prefix) :]:
                candidates.append((remote, ref[len(prefix) :]))
    if len(candidates) != 1:
        raise RuntimeError(
            "could not uniquely discover the repository remote default branch; "
            "set the remote HEAD or provide an adapter-specific configuration"
        )
    return candidates[0]


def _verify_pr(runner: Runner, branch: str, base_branch: str) -> dict[str, object]:
    try:
        result = runner(
            [
                "gh",
                "pr",
                "view",
                "--json",
                "state,headRefName,baseRefName,mergedAt,mergeCommit,url",
            ],
            True,
        )
        data = json.loads(result.stdout)
    except (RuntimeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"cannot verify the pull request through the platform adapter: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError("pull request adapter returned a non-object response")
    if data.get("state") != "MERGED":
        raise RuntimeError("pull request is not merged; no cleanup was attempted")
    if data.get("headRefName") != branch:
        raise RuntimeError("pull request head branch does not match the current Work Item branch")
    if data.get("baseRefName") != base_branch:
        raise RuntimeError("pull request base branch does not match the discovered repository base")
    merge_commit = data.get("mergeCommit")
    if not isinstance(merge_commit, dict) or not merge_commit.get("oid"):
        raise RuntimeError("merged pull request has no authoritative merge commit")
    if not data.get("mergedAt"):
        raise RuntimeError("merged pull request has no merge timestamp")
    return data


def _require_clean_worktree(runner: Runner) -> None:
    status = runner(["status", "--porcelain", "--untracked-files=all"], False)
    if status.returncode != 0:
        raise RuntimeError("cannot inspect repository worktree")
    if status.stdout.strip():
        raise RuntimeError("worktree or index is not clean; cleanup stopped")


def _base_worktree_path(runner: Runner, base_branch: str) -> str | None:
    """Find a worktree that currently owns the repository base branch."""
    result = runner(["worktree", "list", "--porcelain"], False)
    if result.returncode != 0:
        raise RuntimeError("cannot inspect Git worktrees")
    path: str | None = None
    for block in result.stdout.split("\n\n"):
        lines = block.splitlines()
        if not lines or not lines[0].startswith("worktree "):
            continue
        branch = next(
            (
                line.removeprefix("branch refs/heads/")
                for line in lines
                if line.startswith("branch ")
            ),
            None,
        )
        if branch == base_branch:
            path = lines[0].removeprefix("worktree ")
            break
    return path


def _in_worktree(runner: Runner, path: str) -> Runner:
    """Run Git commands against a designated worktree without changing branches."""

    def scoped(args: Sequence[str], check: bool = False) -> CommandResult:
        return runner(["-C", path, *args], check)

    return scoped


def _remote_branch_absent(runner: Runner, remote: str, branch: str) -> None:
    result = runner(["ls-remote", "--exit-code", "--heads", remote, branch], False)
    if result.returncode == 0:
        raise RuntimeError("remote work branch still exists")
    if result.returncode != 2:
        raise RuntimeError("could not verify remote work branch deletion")


def _delete_remote_branch(runner: Runner, remote: str, branch: str) -> None:
    """Delete a remote branch and accept an externally completed deletion."""
    runner(["push", remote, "--delete", branch], False)
    runner(["fetch", remote, "--prune"], True)
    _remote_branch_absent(runner, remote, branch)


def close_work_item(task: str, runner: Runner = _run_git) -> dict[str, str]:
    contract_path = _verify_archived_evidence(task)
    branch_result = runner(["branch", "--show-current"], False)
    if branch_result.returncode != 0 or not branch_result.stdout.strip():
        raise RuntimeError("closure must start from the Work Item branch, not a detached HEAD")
    work_branch = branch_result.stdout.strip()
    remote, base_branch = _discover_base(runner)
    if work_branch == base_branch:
        raise RuntimeError(
            "current branch is the repository base branch, not the still-identifiable Work Item branch; "
            "run ai-close-work-item from the merged Work Item branch before deleting it, then let closure "
            "synchronize the base and remove local/remote branches"
        )
    _require_clean_worktree(runner)
    pr = _verify_pr(runner, work_branch, base_branch)

    base_path = _base_worktree_path(runner, base_branch)
    base_runner = _in_worktree(runner, base_path) if base_path else runner
    if base_path:
        _require_clean_worktree(base_runner)
    else:
        runner(["switch", base_branch], True)
    base_runner(["fetch", remote, "--prune"], True)
    base_runner(["merge", "--ff-only", f"{remote}/{base_branch}"], True)
    local_base = base_runner(["rev-parse", base_branch], True).stdout.strip()
    remote_base = runner(["rev-parse", f"{remote}/{base_branch}"], True).stdout.strip()
    if local_base != remote_base:
        raise RuntimeError("base branch is not synchronized with the remote after fast-forward")

    # A merged PR is the authority for deleting a branch. -D is intentional here:
    # squash and rebase merges do not make the source ref an ancestor of base.
    if base_path:
        runner(["switch", "--detach", "HEAD"], True)
    runner(["branch", "-D", work_branch], True)
    _delete_remote_branch(runner, remote, work_branch)
    final_branch = base_runner(["branch", "--show-current"], True).stdout.strip()
    if final_branch != base_branch:
        raise RuntimeError("repository is not on the synchronized base branch")
    _require_clean_worktree(base_runner)
    final_local = base_runner(["rev-parse", base_branch], True).stdout.strip()
    final_remote = runner(["rev-parse", f"{remote}/{base_branch}"], True).stdout.strip()
    if final_local != final_remote:
        raise RuntimeError("local base branch no longer matches the remote base branch")

    return {
        "task": task,
        "contract": contract_path.relative_to(PROJECT_ROOT).as_posix(),
        "pullRequest": str(pr.get("url", "")),
        "workBranch": work_branch,
        "baseRemote": remote,
        "baseBranch": base_branch,
        "baseCommit": final_local,
        "state": "closed",
        "repositoryState": "ready_for_next_work_item",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Close a completed Work Item safely.")
    parser.add_argument("--task", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = close_work_item(args.task, _default_runner)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Work Item lifecycle: not closed\nReason: {exc}", file=sys.stderr)
        return 1
    print("Work Item lifecycle: closed")
    print(f"Pull request: merged ({result['pullRequest']})")
    print(f"Local work branch: deleted ({result['workBranch']})")
    print(f"Remote work branch: deleted ({result['workBranch']})")
    print(
        f"Local {result['baseBranch']}: synchronized with {result['baseRemote']}/{result['baseBranch']}"
    )
    print("Repository state: ready for next Work Item")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
