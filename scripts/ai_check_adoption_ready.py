#!/usr/bin/env python3
"""Check static completeness of project-specific AI Cockpit adoption configuration."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from ai_check_guard_calibration import calibration_issues
from ai_project_profile import load_profile


PLACEHOLDER_MARKERS = ("configure PROJECT_", "No project")
QUALITY_VARIABLES = ("PROJECT_FORMAT_CHECK", "PROJECT_TEST", "PROJECT_LINT")
TRIVIAL_COMMANDS = {":", "true", "/bin/true"}
TEMPLATE_EVIDENCE_FILES = (
    "templates/agents/AI_COCKPIT_RULES.md",
    "templates/glossary.md",
    "templates/make/Makefile.ai",
    ".ai/work-items/_templates/work_item_contract.example.json",
    ".ai/work-items/_templates/work_item_summary.example.json",
)


def template_distribution_evidence(root: Path) -> list[str]:
    evidence: list[str] = []
    for relative in TEMPLATE_EVIDENCE_FILES:
        path = root / relative
        if not path.is_file():
            continue
        try:
            if path.read_text(encoding="utf-8").strip():
                evidence.append(relative)
        except OSError:
            continue
    return evidence


def template_exemption(
    profile: dict[str, object], root: Path, *, execution_mode: str | None = None
) -> tuple[bool, list[str]]:
    """Return an explicit, inspectable template-maintenance exemption.

    Role is intent, not identity: it must be corroborated by a checked-in
    template distribution layout and an explicit maintenance mode.
    """
    evidence: list[str] = []
    if profile.get("repositoryRole") == "template":
        evidence.append("repositoryRole=template")
    mode = execution_mode or os.environ.get("AI_COCKPIT_EXECUTION_MODE")
    if mode == "template_maintenance":
        evidence.append("AI_COCKPIT_EXECUTION_MODE=template_maintenance")
    distribution = template_distribution_evidence(root)
    if len(distribution) == len(TEMPLATE_EVIDENCE_FILES):
        evidence.append("template distribution evidence present")
    return len(evidence) == 3, evidence


def readiness_role_message(root: Path) -> str:
    profile, issues = load_profile(root / ".ai" / "project_profile.yaml", require_approval=True)
    if issues:
        return "role=unknown; no exemption; fix Project Profile then calibrate adopted-project readiness"
    exempt, evidence = template_exemption(profile, root)
    if exempt:
        return (
            "role=template maintenance; exemption=project calibration only; evidence="
            + "; ".join(evidence)
        )
    return "role=adopted or unconfirmed template; exemption=none; migrate with Profile, Guards, quality commands, Coverage, and CI calibration"


def quality_commands(text: str) -> dict[str, str]:
    commands: dict[str, str] = {}
    for name in QUALITY_VARIABLES:
        match = re.search(rf"^\s*{name}\s*[?:+]?=\s*(\S.*)$", text, re.MULTILINE)
        if match:
            commands[name] = match.group(1).strip()
    return commands


def readiness_failures(root: Path) -> list[str]:
    failures: list[str] = []
    profile, profile_issues = load_profile(
        root / ".ai" / "project_profile.yaml", require_approval=True
    )
    role = profile.get("repositoryRole") if not profile_issues else None
    if not profile_issues and role not in {"template", "adopted"}:
        failures.append(
            "set repositoryRole: adopted after migration (or template with explicit template_maintenance execution mode); missing role is fail-closed"
        )
    if not profile_issues and profile.get("repositoryRole") == "template":
        exempt, evidence = template_exemption(profile, root)
        if exempt:
            return []
        failures.append(
            "template role is not enough for readiness exemption; run with AI_COCKPIT_EXECUTION_MODE=template_maintenance "
            "and retain verified template distribution evidence, or migrate to repositoryRole: adopted and calibrate Profile, Guards, quality commands, Coverage, and CI"
        )

    stack = root / "Makefile.ai.stack"
    if not stack.is_file():
        failures.append("select and customize Makefile.ai.stack project quality commands")
    else:
        text = stack.read_text(encoding="utf-8")
        commands = quality_commands(text)
        if any(marker in text for marker in PLACEHOLDER_MARKERS) or len(commands) != len(
            QUALITY_VARIABLES
        ):
            failures.append("replace all Makefile.ai.stack project quality placeholders")
        elif any(command in TRIVIAL_COMMANDS for command in commands.values()):
            failures.append("replace trivial no-op project quality commands such as true or :")

    coverage = root / ".ai" / "guards" / "coverage_policy.yaml"
    coverage_text = coverage.read_text(encoding="utf-8") if coverage.is_file() else ""
    if not re.search(r"^adoptionReviewed:\s*true\s*$", coverage_text, re.MULTILINE):
        failures.append(
            "review production/test paths in .ai/guards/coverage_policy.yaml and set adoptionReviewed: true"
        )

    failures.extend(f"fix Project Profile: {issue}" for issue in profile_issues)
    if not profile_issues:
        failures.extend(
            f"calibrate Guard policies: {issue}" for issue in calibration_issues(root, profile)
        )

    ci_files = list((root / ".github" / "workflows").glob("*.y*ml"))
    gitlab = root / ".gitlab-ci.yml"
    if gitlab.is_file():
        ci_files.append(gitlab)
    ci_text = "\n".join(path.read_text(encoding="utf-8") for path in ci_files)
    for target in ("ai-cockpit-quality", "check-ai-pr"):
        if not any(
            not line.lstrip().startswith("#")
            and re.search(rf"\bmake\s+{re.escape(target)}\b", line)
            for line in ci_text.splitlines()
        ):
            failures.append(f"configure {target} in GitHub Actions or GitLab CI")

    codeowners = root / ".github" / "CODEOWNERS"
    security = root / "SECURITY.md"
    if role == "adopted":
        if not codeowners.is_file():
            failures.append(
                ".github/CODEOWNERS is missing; configure at least one external owner rule"
            )
        else:
            codeowners_text = codeowners.read_text(encoding="utf-8")
            rules = [
                line.strip()
                for line in codeowners_text.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
            placeholder = re.compile(r"(?:@owner|REPLACE_WITH|placeholder)", re.IGNORECASE)
            if not rules or any(placeholder.search(line) for line in rules):
                failures.append("replace placeholder CODEOWNERS owners before adoption readiness")
            elif not any(
                len(line.split()) >= 2 and line.split()[1].startswith(("@", "mailto:"))
                for line in rules
            ):
                failures.append(
                    "configure at least one valid CODEOWNERS owner rule before adoption readiness"
                )

        if not security.is_file():
            failures.append(
                "SECURITY.md is missing; configure a private vulnerability reporting channel"
            )
        else:
            security_text = security.read_text(encoding="utf-8")
            template_markers = re.compile(
                r"(?:governance template|replace this|before production adoption|template boundary)",
                re.IGNORECASE,
            )
            if template_markers.search(security_text) or not re.search(
                r"private.{0,80}(?:report|vulnerab|security)|(?:report|vulnerab|security).{0,80}private",
                security_text,
                re.IGNORECASE | re.DOTALL,
            ):
                failures.append(
                    "replace template SECURITY.md instructions before adoption readiness"
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to inspect.")
    args = parser.parse_args()
    failures = readiness_failures(Path(args.root).resolve())
    print(f"adoption role: {readiness_role_message(Path(args.root).resolve())}")
    if failures:
        print("AI Cockpit static adoption configuration is incomplete:")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("AI Cockpit static adoption configuration check passed")
    print(
        "This does not prove command effectiveness; require make ai-cockpit-quality and check-ai-pr in CI."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
