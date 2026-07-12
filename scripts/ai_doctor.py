#!/usr/bin/env python3
"""Report AI Cockpit environment and adoption readiness without modifying files."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ai_check_adoption_ready import readiness_failures, readiness_role_message


def command_ok(root: Path, *command: str) -> bool:
    try:
        return subprocess.run(
            command, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        ).returncode == 0
    except OSError:
        return False


def diagnose(root: Path) -> tuple[list[str], list[str], list[str]]:
    passed: list[str] = []
    warnings: list[str] = []
    failures: list[str] = []

    if sys.version_info >= (3, 10):
        passed.append(f"Python {sys.version_info.major}.{sys.version_info.minor} satisfies 3.10+")
    else:
        failures.append("Python 3.10 or newer is required")
    for command in ("git", "make"):
        (passed if shutil.which(command) else failures).append(
            f"{command} is available" if shutil.which(command) else f"{command} is required on PATH"
        )
    if os.name == "posix":
        passed.append("POSIX runtime detected")
    else:
        failures.append("A POSIX shell environment is required; use WSL on Windows")

    if command_ok(root, "git", "rev-parse", "--is-inside-work-tree"):
        passed.append("Git repository detected")
    else:
        failures.append("Run inside a Git repository")
    if command_ok(root, "git", "rev-parse", "--verify", "HEAD"):
        passed.append("Initial Git commit detected")
    else:
        failures.append("Create an initial Git commit before ai-start or --create-adoption")
    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, text=True,
            capture_output=True, check=False,
        ).stdout.strip()
    except OSError:
        dirty = ""
    if dirty:
        warnings.append("Git worktree is dirty; --create-adoption requires a clean worktree")
    else:
        passed.append("Git worktree is clean")

    stack = root / "Makefile.ai.stack"
    if not stack.is_file():
        warnings.append("Makefile.ai.stack is missing; install or select a stack preset")
    else:
        text = stack.read_text(encoding="utf-8")
        if "configure PROJECT_" in text or "No project" in text:
            warnings.append("Project quality commands are still placeholders/fail-closed defaults")
        else:
            passed.append("Project quality commands are configured")
    coverage = root / ".ai" / "guards" / "coverage_policy.yaml"
    if coverage.is_file():
        warnings.append("Review Coverage Guard production/test paths against the project layout")
    else:
        warnings.append("Coverage Guard policy is missing")
    if (root / ".github" / "workflows").is_dir() or (root / ".gitlab-ci.yml").is_file():
        passed.append("CI configuration detected; verify merge-base wiring manually")
    else:
        warnings.append("No GitHub Actions or GitLab CI configuration detected for check-ai-pr")
    if readiness_failures(root):
        warnings.append(readiness_role_message(root))
        warnings.append("Run make check-ai-adoption-ready before enabling production gates")
    else:
        passed.append(readiness_role_message(root))
        passed.append("Adoption readiness configuration is complete")
    return passed, warnings, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to inspect.")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    passed, warnings, failures = diagnose(root)
    for item in passed:
        print(f"[PASS] {item}")
    for item in warnings:
        print(f"[WARN] {item}")
    for item in failures:
        print(f"[FAIL] {item}")
    print(f"doctor summary: {len(passed)} passed, {len(warnings)} warning(s), {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
