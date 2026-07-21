#!/usr/bin/env python3
"""Run a reproducible adopter lifecycle in an isolated local Git repository."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def run() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ai-cockpit-adopter-") as name:
        root = Path(name)
        remote, repo, worktree = root / "remote.git", root / "adopter", root / "upgrade-worktree"
        git(root, "init", "--bare", str(remote))
        git(root, "init", str(repo))
        git(repo, "config", "user.email", "adopter@example.invalid")
        git(repo, "config", "user.name", "Adopter Fixture")
        (repo / "README.md").write_text("adopter baseline\n", encoding="utf-8")
        git(repo, "add", "README.md")
        git(repo, "commit", "-m", "baseline")
        git(repo, "branch", "-M", "main")
        git(repo, "remote", "add", "origin", str(remote))
        git(repo, "push", "-u", "origin", "main")
        baseline = git(repo, "rev-parse", "HEAD")
        git(repo, "worktree", "add", "-b", "upgrade", str(worktree), "main")
        (worktree / "README.md").write_text("adopter upgraded\n", encoding="utf-8")
        git(worktree, "add", "README.md")
        git(worktree, "commit", "-m", "upgrade")
        upgrade = git(worktree, "rev-parse", "HEAD")
        git(repo, "push", "origin", "upgrade")
        git(repo, "merge", "--no-ff", "upgrade", "-m", "merge adopter upgrade")
        merge = git(repo, "rev-parse", "HEAD")
        git(repo, "push", "origin", "main")
        git(repo, "worktree", "remove", str(worktree))
        git(repo, "branch", "-D", "upgrade")
        git(repo, "push", "origin", "--delete", "upgrade")
        git(repo, "checkout", "-b", "rollback", "main")
        git(repo, "revert", "-m", "1", merge, "--no-edit")
        rollback = git(repo, "rev-parse", "HEAD")
        git(repo, "merge", "--no-ff", "rollback", "-m", "merge adopter rollback")
        git(repo, "push", "origin", "main")
        git(repo, "checkout", "main")
        git(repo, "branch", "-D", "rollback")
        return {
            "repository": "isolated temporary adopter repository",
            "defaultBranch": "main",
            "remote": "local bare origin",
            "baselineCommit": baseline,
            "upgradeCommit": upgrade,
            "mergeCommit": merge,
            "rollbackCommit": rollback,
            "upgradeWorktreeRemoved": not worktree.exists(),
            "localBranchesCleaned": git(repo, "branch", "--format=%(refname:short)") == "main",
            "remoteBranchesCleaned": git(repo, "ls-remote", "--heads", "origin").count(
                "refs/heads/"
            )
            == 1,
            "enterpriseAssurance": "not_claimed",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(run(), indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
