#!/usr/bin/env python3
"""Validate documentation front matter and supported-stack lists."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from install_ai_cockpit import STACKS


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FRONT_MATTER = ("author", "title", "description")
README_FILES = ("README.md", "README.ja.md", "README.zh-CN.md")
README_CAPABILITY_MARKER = "<!-- release-capabilities: auditable-adoption,sha256-verification -->"
README_PREREQUISITE_MARKER = (
    "<!-- install-prerequisites: python3.10,git-initial-commit,curl,gnu-make,posix -->"
)
VERIFIED_STACKS: tuple[str, ...] = (
    "python",
    "go",
    "rust",
    "typescript",
    "java",
    "kotlin",
    "ruby",
    "php",
    "csharp",
    "flutter",
    "android",
    "swift",
)
WORKFLOW_IMPLEMENTED_STACKS: tuple[str, ...] = ()
TEMPLATE_ONLY_STACKS = ("generic",)
JAPANESE_STYLE_RULES = {
    "Gemini, Claude, Codex": "use Japanese punctuation between agent names",
    "実行時の安全性を確保": "do not overstate command registry guarantees",
    "Use this stack preset": "translate instructional prose into Japanese",
    "Suggested guard patterns": "translate instructional prose into Japanese",
    "阻断": "use Japanese terminology such as ブロッキング",
    "確信度": "use 信頼度 for confidence in Japanese documentation",
}


def documentation_files(root: Path) -> list[Path]:
    files = [root / name for name in README_FILES]
    files.append(root / ".ai" / "README.md")
    files.append(root / ".ai" / "glossary.md")
    files.extend(sorted((root / "docs").rglob("*.md")))
    files.extend(sorted((root / "examples").glob("*/README.md")))
    return files


def front_matter_errors(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{path}: missing YAML front matter"]
    closing = text.find("\n---\n", 4)
    if closing < 0:
        return [f"{path}: unterminated YAML front matter"]
    block = text[4:closing]
    keys = {
        match.group(1)
        for line in block.splitlines()
        if (match := re.match(r"^([A-Za-z][A-Za-z0-9_-]*):", line))
    }
    return [
        f"{path}: front matter missing {key}" for key in REQUIRED_FRONT_MATTER if key not in keys
    ]


def tier_marker() -> str:
    return (
        "<!-- stack-tiers: verified="
        + ",".join(VERIFIED_STACKS)
        + "; workflow-implemented="
        + ",".join(WORKFLOW_IMPLEMENTED_STACKS)
        + "; preset-only="
        + ",".join(TEMPLATE_ONLY_STACKS)
        + " -->"
    )


def stack_errors(root: Path) -> list[str]:
    ordered_stacks = [
        "generic",
        "rust",
        "flutter",
        "typescript",
        "python",
        "go",
        "java",
        "android",
        "kotlin",
        "swift",
        "ruby",
        "php",
        "csharp",
    ]
    if set(ordered_stacks) != STACKS:
        return [
            "scripts/check_docs_metadata.py: canonical stack order does not match installer STACKS"
        ]

    readme_list = ", ".join(ordered_stacks)
    marker = tier_marker()
    errors = []
    for name in README_FILES:
        text = (root / name).read_text(encoding="utf-8")
        if readme_list not in text:
            errors.append(f"{name}: supported-stack list does not match installer STACKS")
        if marker not in text:
            errors.append(f"{name}: stack compatibility tiers do not match executable CI evidence")

    configuration = (root / "docs" / "configuration.md").read_text(encoding="utf-8")
    configuration_list = "\n".join(ordered_stacks)
    if configuration_list not in configuration:
        errors.append("docs/configuration.md: supported-stack list does not match installer STACKS")
    if marker not in configuration:
        errors.append(
            "docs/configuration.md: stack compatibility tiers do not match executable CI evidence"
        )
    return errors


def installation_command_errors(root: Path) -> list[str]:
    release = json.loads((root / "release.json").read_text(encoding="utf-8"))
    release_tag = release["releaseTag"]
    archive_capability = release["capabilities"]["sha256ArchiveVerification"]
    if isinstance(archive_capability, dict):
        sha256_published = (
            archive_capability.get("supported") is True
            and archive_capability.get("verified") is True
        )
    else:
        sha256_published = archive_capability is True
    quality_target = release["publicContract"]["projectQualityTarget"]
    quality_marker = f"<!-- public-quality-target: {quality_target} -->"
    errors = []
    for path in documentation_files(root):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        if relative in README_FILES:
            if re.search(r"\bv\d+\.\d+\.\d+\b", text):
                errors.append(
                    f"{relative}: primary README must not hardcode a concrete release version"
                )
            if "main/release.json" not in text or "${RELEASE_TAG}/install.sh" not in text:
                errors.append(
                    f"{relative}: primary install command must resolve the tagged installer from release.json"
                )
            if README_CAPABILITY_MARKER not in text:
                errors.append(f"{relative}: release capability marker is missing or inconsistent")
            prerequisite_position = text.find(README_PREREQUISITE_MARKER)
            install_position = text.find('sh "$INSTALLER" --stack')
            if (
                prerequisite_position < 0
                or install_position < 0
                or prerequisite_position > install_position
            ):
                errors.append(
                    f"{relative}: installation prerequisites must precede the primary install command"
                )
            if quality_marker not in text:
                errors.append(f"{relative}: public quality target differs from release.json")
            readiness_lines = [
                line
                for line in text.splitlines()
                if "`check-ai-pr`" in line
                and (
                    "readiness" in line.lower()
                    or "導入準備" in line
                    or "Adoption Readiness" in line
                )
            ]
            if not any(f"`{quality_target}`" in line for line in readiness_lines):
                errors.append(
                    f"{relative}: readiness guidance does not use the public quality target"
                )
            if "--create-adoption" not in text:
                errors.append(
                    f"{relative}: primary install command must create auditable adoption evidence"
                )
            if 'STACK="${STACK:-generic}"' not in text or '--stack "$STACK"' not in text:
                errors.append(
                    f"{relative}: primary install command must use an explicit generic-default STACK variable"
                )
            ordered_steps = (
                "--create-adoption",
                "make ai-finish TASK=adopt_ai_cockpit",
                "git commit",
                "make check-ai-pr",
                "make ai-start TASK=configure_ai_cockpit",
                "make cockpit-doctor",
            )
            positions = [text.find(step) for step in ordered_steps]
            if any(position < 0 for position in positions) or positions != sorted(positions):
                errors.append(
                    f"{relative}: primary adoption flow must finish, audit, and start configuration governance before calibration"
                )
        for number, line in enumerate(text.splitlines(), start=1):
            if (
                "raw.githubusercontent.com/spirex-ds-dev/ai-cockpit-template/main/install.sh"
                in line
            ):
                errors.append(
                    f"{relative}:{number}: remote installer must use a fixed tag or commit"
                )
            if (
                "--stack" in line
                and "install" in line
                and "--upgrade" not in line
                and "--update-makefile" not in line
            ):
                errors.append(
                    f"{relative}:{number}: install command with --stack requires --update-makefile"
                )
            if (
                relative.startswith("examples/")
                and "--stack" in line
                and "install" in line
                and "--create-adoption" not in line
            ):
                errors.append(
                    f"{relative}:{number}: example install command must create auditable adoption evidence"
                )
            for tag in re.findall(r"v\d+\.\d+\.\d+", line):
                if tag != release_tag:
                    errors.append(
                        f"{relative}:{number}: documented release {tag} does not match release.json {release_tag}"
                    )
            if (
                not sha256_published
                and "AI_COCKPIT_TEMPLATE_SHA256" in line
                and "does **not** implement" not in line
                and "additional assertion" not in line
                and "追加のアサーション" not in line
                and "附加断言" not in line
            ):
                errors.append(
                    f"{relative}:{number}: SHA256 verification is not published for {release_tag}"
                )
    install_script = (root / "install.sh").read_text(encoding="utf-8")
    if f'REF="${{AI_COCKPIT_TEMPLATE_REF:-{release_tag}}}"' not in install_script:
        errors.append("install.sh: default ref does not match release.json")
    installation = (root / "docs" / "getting-started" / "installation.md").read_text(
        encoding="utf-8"
    )
    if quality_marker not in installation:
        errors.append(
            "docs/getting-started/installation.md: public quality target differs from release.json"
        )
    if f"make {quality_target}\nmake check-ai-adoption-ready" not in installation:
        errors.append(
            "docs/getting-started/installation.md: readiness commands do not use the public quality target"
        )
    return errors


def japanese_style_errors(root: Path) -> list[str]:
    errors = []
    paths = [
        root / "README.ja.md",
        *sorted((root / "docs").rglob("*.md")),
        *sorted((root / "examples").glob("*/README.md")),
    ]
    for path in paths:
        relative = path.relative_to(root).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for phrase, reason in JAPANESE_STYLE_RULES.items():
                if phrase in line:
                    errors.append(f"{relative}:{number}: Japanese style: {reason}: {phrase}")
            if re.search(r"\d+つ", line):
                errors.append(
                    f"{relative}:{number}: Japanese style: add a space between a number and つ"
                )
    return errors


def check_repository(root: Path) -> list[str]:
    errors = []
    for path in documentation_files(root):
        errors.extend(front_matter_errors(path))
    errors.extend(stack_errors(root))
    errors.extend(installation_command_errors(root))
    errors.extend(japanese_style_errors(root))
    return errors


def main() -> int:
    errors = check_repository(ROOT)
    if errors:
        print("documentation metadata check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("documentation metadata check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
