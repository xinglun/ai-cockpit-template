#!/usr/bin/env python3
"""Check static completeness of project-specific AI Cockpit adoption configuration."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PLACEHOLDER_MARKERS = ("configure PROJECT_", "No project")
QUALITY_VARIABLES = ("PROJECT_FORMAT_CHECK", "PROJECT_TEST", "PROJECT_LINT")
TRIVIAL_COMMANDS = {":", "true", "/bin/true"}


def quality_commands(text: str) -> dict[str, str]:
    commands: dict[str, str] = {}
    for name in QUALITY_VARIABLES:
        match = re.search(rf"^\s*{name}\s*[?:+]?=\s*(\S.*)$", text, re.MULTILINE)
        if match:
            commands[name] = match.group(1).strip()
    return commands


def readiness_failures(root: Path) -> list[str]:
    failures: list[str] = []
    stack = root / "Makefile.ai.stack"
    if not stack.is_file():
        failures.append("select and customize Makefile.ai.stack project quality commands")
    else:
        text = stack.read_text(encoding="utf-8")
        commands = quality_commands(text)
        if any(marker in text for marker in PLACEHOLDER_MARKERS) or len(commands) != len(QUALITY_VARIABLES):
            failures.append("replace all Makefile.ai.stack project quality placeholders")
        elif any(command in TRIVIAL_COMMANDS for command in commands.values()):
            failures.append("replace trivial no-op project quality commands such as true or :")

    coverage = root / ".ai" / "guards" / "coverage_policy.yaml"
    coverage_text = coverage.read_text(encoding="utf-8") if coverage.is_file() else ""
    if not re.search(r"^adoptionReviewed:\s*true\s*$", coverage_text, re.MULTILINE):
        failures.append(
            "review production/test paths in .ai/guards/coverage_policy.yaml and set adoptionReviewed: true"
        )

    ci_files = list((root / ".github" / "workflows").glob("*.y*ml"))
    gitlab = root / ".gitlab-ci.yml"
    if gitlab.is_file():
        ci_files.append(gitlab)
    if not any(
        any(
            not line.lstrip().startswith("#") and re.search(r"\bmake\s+check-ai-pr\b", line)
            for line in path.read_text(encoding="utf-8").splitlines()
        )
        for path in ci_files
    ):
        failures.append("configure check-ai-pr in GitHub Actions or GitLab CI")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to inspect.")
    args = parser.parse_args()
    failures = readiness_failures(Path(args.root).resolve())
    if failures:
        print("AI Cockpit static adoption configuration is incomplete:")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("AI Cockpit static adoption configuration check passed")
    print("This does not prove command effectiveness; require make quality and check-ai-pr in CI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
