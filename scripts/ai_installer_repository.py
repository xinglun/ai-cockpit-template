"""Repository adapter boundary for installer Git operations."""

import os
import subprocess  # nosec B404
from pathlib import Path


def git_target_args(target: Path) -> list[str]:
    return [f"--git-dir={target / '.git'}", f"--work-tree={target}"]


def clean_git_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def run_git(target: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607
        ["git", *git_target_args(target), *args],
        cwd=target,
        text=True,
        capture_output=True,
        check=False,
        env=clean_git_environment(),
    )


def git_records(output: str) -> list[str]:
    return (
        [item for item in output.split("\0") if item]
        if "\0" in output
        else [line for line in output.splitlines() if line]
    )
