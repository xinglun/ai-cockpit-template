#!/usr/bin/env python3
"""Validate global consistency across distribution, docs, presets, CI, and checks."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from check_docs_metadata import README_FILES, check_repository
from check_release_distribution import exercise_installer
from install_ai_cockpit import STACKS


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".ai" / "cockpit" / "system_invariants.json"


def make_targets(path: Path) -> set[str]:
    return {
        match.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"^([A-Za-z0-9_.-]+)(?:\s+[^:]*)?:", line))
    }


def check_ids(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    block = text.split("checks:", 1)[1].split("selectionRules:", 1)[0]
    return set(re.findall(r"^  ([A-Za-z][A-Za-z0-9]+):$", block, re.MULTILINE))


def local_link_issues(path: Path) -> list[str]:
    issues = []
    text = path.read_text(encoding="utf-8")
    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if link.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = (path.parent / link.split("#", 1)[0]).resolve()
        if not target.exists():
            issues.append(f"{path.relative_to(ROOT)}: broken local link: {link}")
    return issues


def release_contract_issues(root: Path, release: dict[str, Any]) -> list[str]:
    target = release.get("publicContract", {}).get("projectQualityTarget")
    if not isinstance(target, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", target):
        return ["release.json public project quality target is missing or invalid"]
    marker = f"<!-- public-quality-target: {target} -->"
    paths = [*(root / name for name in README_FILES), root / "docs" / "installation.md"]
    return [
        f"{path.relative_to(root)}: public quality target differs from release.json"
        for path in paths
        if marker not in path.read_text(encoding="utf-8")
    ]


def invariant_issues(root: Path = ROOT) -> list[str]:
    issues = check_repository(root)
    try:
        manifest: dict[str, Any] = json.loads((root / MANIFEST.relative_to(ROOT)).read_text(encoding="utf-8"))
        release = json.loads((root / "release.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [*issues, f"failed to load invariant metadata: {exc}"]
    issues.extend(release_contract_issues(root, release))
    stacks = manifest.get("stacks", [])
    if set(stacks) != STACKS:
        issues.append("system manifest stack list differs from installer STACKS")
    presets = {path.stem for path in (root / "templates" / "stacks").glob("*.mk")}
    if presets != STACKS:
        issues.append("stack presets differ from installer STACKS")
    compatibility = manifest.get("compatibility", {})
    verified = compatibility.get("verified", []) if isinstance(compatibility, dict) else []
    workflow_implemented = compatibility.get("workflowImplemented", []) if isinstance(compatibility, dict) else []
    preset_only = compatibility.get("presetOnly", []) if isinstance(compatibility, dict) else []
    tiers = (set(verified), set(workflow_implemented), set(preset_only))
    if set().union(*tiers) != STACKS or any(
        left & right for index, left in enumerate(tiers) for right in tiers[index + 1:]
    ):
        issues.append("compatibility tiers must partition all supported stacks")
    workflow = (root / ".github" / "workflows" / "compatibility.yml").read_text(encoding="utf-8")
    for stack in [*verified, *workflow_implemented]:
        if stack not in workflow:
            issues.append(f"verified stack is missing from compatibility CI: {stack}")
    tier_marker = (
        f"<!-- stack-tiers: verified={','.join(verified)}; "
        f"workflow-implemented={','.join(workflow_implemented)}; preset-only={','.join(preset_only)} -->"
    )
    flow_marker = f"<!-- governance-flow: {','.join(manifest.get('governanceFlow', []))} -->"
    capability_marker = f"<!-- release-capabilities: {','.join(manifest.get('releaseCapabilities', []))} -->"
    for name in README_FILES:
        text = (root / name).read_text(encoding="utf-8")
        for marker, label in ((tier_marker, "compatibility tiers"), (flow_marker, "governance flow"), (capability_marker, "release capabilities")):
            if marker not in text:
                issues.append(f"{name}: {label} differ from system manifest")
        install_line = next((line for line in text.splitlines() if "sh \"$INSTALLER\" --stack" in line), "")
        for flag in manifest.get("recommendedInstallFlags", []):
            if flag not in install_line:
                issues.append(f"{name}: primary install command is missing {flag}")
    default_match = re.search(r'^REF="\$\{AI_COCKPIT_TEMPLATE_REF:-(v\d+\.\d+\.\d+)\}"', (root / "install.sh").read_text(encoding="utf-8"), re.MULTILINE)
    if not default_match or default_match.group(1) != release.get("releaseTag"):
        issues.append("install.sh default version differs from release.json")
    targets = make_targets(root / "Makefile") | make_targets(root / "templates" / "make" / "Makefile.ai")
    registry_ids = check_ids(root / ".ai" / "cockpit" / "checks.yaml")
    for definition in re.findall(r"^    command(?:Template)?:\s+make\s+([A-Za-z0-9_.-]+)", (root / ".ai" / "cockpit" / "checks.yaml").read_text(encoding="utf-8"), re.MULTILINE):
        if definition not in targets:
            issues.append(f"checks.yaml references missing Make target: {definition}")
    contract_template = json.loads((root / ".ai" / "work-items" / "_templates" / "work_item_contract.example.json").read_text(encoding="utf-8"))
    for item in contract_template.get("verification", []):
        if isinstance(item, dict) and item.get("check") not in registry_ids:
            issues.append(f"Contract example references unknown Check ID: {item.get('check')}")
    documentation = [
        *(root / name for name in README_FILES),
        *sorted((root / "docs").glob("*.md")),
        *sorted((root / "examples").glob("*/README.md")),
    ]
    documented_targets: set[str] = set()
    for path in documentation:
        text = path.read_text(encoding="utf-8")
        documented_targets.update(re.findall(r"(?m)^[ \t]*make[ \t]+([A-Za-z0-9_.-]+)", text))
        documented_targets.update(re.findall(r"`make[ \t]+([A-Za-z0-9_.-]+)", text))
    for target in documented_targets:
        if target not in targets:
            issues.append(f"documentation references missing Make target: {target}")
    for path in documentation:
        issues.extend(local_link_issues(path))
    try:
        exercise_installer(
            (root / "install.sh").read_bytes(),
            tag=str(release["releaseTag"]),
            sha256_supported=bool(release["capabilities"]["sha256ArchiveVerification"]),
        )
    except (KeyError, TypeError, RuntimeError) as exc:
        issues.append(f"local distribution capability contract failed: {exc}")
    return issues


def main() -> int:
    issues = invariant_issues()
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print("AI Cockpit system invariants passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
