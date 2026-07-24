#!/usr/bin/env python3
"""Fail-closed checks that must pass before expensive release CI starts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from release_archive import canonical_archive_sha, canonical_source_tree


class ReleasePreflightError(ValueError):
    """Raised when a release candidate is not frozen and source-bound."""


def validate_release_projection(
    *, state: dict[str, Any], release: dict[str, Any], candidate: dict[str, Any]
) -> list[str]:
    """Reject canonical-state/projection drift before archive generation."""
    issues: list[str] = []
    state_name = state.get("state")
    state_tag = state.get("releaseTag")
    published_tag = release.get("releaseTag")
    candidate_tag = candidate.get("releaseTag")
    if state_name in {"candidate_prepared", "candidate_verified"}:
        if state_tag != candidate_tag:
            issues.append("canonical candidate releaseTag does not match next-release.json")
    elif state_name == "release_published" and state_tag != published_tag:
        issues.append("canonical published releaseTag does not match release.json")
    if state.get("previousRelease") != published_tag:
        issues.append("canonical previousRelease does not match release.json releaseTag")
    if candidate.get("basedOnReleaseTag") != published_tag:
        issues.append("next-release.json basedOnReleaseTag does not match release.json releaseTag")
    if published_tag == candidate_tag:
        issues.append("published and candidate releaseTag values must be distinct")
    return issues


def validate_release_identity(
    *,
    release: dict[str, Any],
    freeze: dict[str, Any],
    release_digests: dict[str, Any],
    source_commit: str,
    tag_target: str,
    metadata_commit: str,
) -> list[str]:
    """Validate the immutable release identity tuple before expensive checks."""
    issues: list[str] = []
    concrete = re.compile(r"^[0-9a-f]{40}$")
    identity = {
        "sourceCommit": source_commit,
        "tagTarget": tag_target,
        "metadataCommit": metadata_commit,
    }
    for name, value in identity.items():
        if not isinstance(value, str) or not concrete.fullmatch(value):
            issues.append(f"{name} must be a concrete 40-character lowercase SHA")
    if source_commit != tag_target:
        issues.append("sourceCommit and tagTarget must identify the same commit")
    for name, value in identity.items():
        if freeze.get(name) != value:
            issues.append(f"freeze {name} does not match the release identity tuple")
        digest_value = release_digests.get(name)
        if not isinstance(digest_value, str) or not concrete.fullmatch(digest_value):
            issues.append(f"release-digests {name} must be a concrete 40-character lowercase SHA")
        elif digest_value != value:
            issues.append(f"release-digests {name} does not match the release identity tuple")
    release_tag = release.get("releaseTag")
    if not isinstance(release_tag, str) or freeze.get("releaseTag") != release_tag:
        issues.append("releaseTag must match between release.json and release-freeze.json")
    if release_digests.get("releaseTag") != release_tag:
        issues.append("release-digests releaseTag does not match release.json")
    return issues


def resolve_source_commit(root: Path, source_ref: str) -> str:
    """Resolve a symbolic or concrete source reference to one commit identity."""
    try:
        result = subprocess.run(  # nosec B603 B607
            ["git", "-C", str(root), "rev-parse", f"{source_ref}^{{commit}}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReleasePreflightError(
            f"source commit reference cannot be resolved: {source_ref!r}"
        ) from exc
    resolved = result.stdout.strip()
    if not resolved:
        raise ReleasePreflightError(f"source commit reference resolved empty: {source_ref!r}")
    return resolved


def resolve_release_identity_ref(root: Path, value: Any, label: str) -> str:
    """Resolve a concrete SHA or controlled origin ref; never accept HEAD."""
    if not isinstance(value, str) or not value or value == "HEAD":
        raise ReleasePreflightError(f"{label} must be a concrete SHA or controlled origin ref")
    concrete = re.compile(r"^[0-9a-f]{40}$")
    controlled_ref = re.compile(r"^origin/[A-Za-z0-9._/-]+$")
    if not concrete.fullmatch(value) and not controlled_ref.fullmatch(value):
        raise ReleasePreflightError(f"{label} uses an unsupported identity reference")
    return resolve_source_commit(root, value)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleasePreflightError(f"{label} is missing or invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleasePreflightError(f"{label} must be a JSON object")
    return value


def validate_release_preflight(
    *,
    release: dict[str, Any],
    freeze: dict[str, Any],
    release_digests: dict[str, Any] | None = None,
    source_commit: str | None = None,
    actual_archive_sha: str,
    source_tree: str,
    active_work_items: list[str],
    archive_count: int,
    archive_max: int,
    archive_enforcement: str = "error",
) -> list[str]:
    issues: list[str] = []
    if active_work_items:
        issues.append(f"active Work Items remain: {', '.join(active_work_items)}")
    if archive_count > archive_max and archive_enforcement != "warning":
        issues.append(f"archiveGrowth={archive_count} exceeds configured maximum {archive_max}")
    if freeze.get("state") != "frozen":
        issues.append("release-freeze.json state must be frozen")
    lifecycle = freeze.get("lifecycle")
    if not isinstance(lifecycle, dict) or lifecycle.get("state") not in {
        "closed_and_synchronized",
        "premerge_finalized",
    }:
        issues.append(
            "release freeze lifecycle must be finalized after Work Item archive and before publication"
        )
    else:
        lifecycle_state = lifecycle.get("state")
        expected_command = (
            "make ai-close-work-item" if lifecycle_state == "closed_and_synchronized" else None
        )
        if lifecycle_state == "premerge_finalized":
            command = lifecycle.get("command")
            if not isinstance(command, str) or not command.startswith(
                "make finalize-release-freeze-premerge TASK="
            ):
                issues.append(
                    "pre-merge release freeze lifecycle command must identify the archived Work Item"
                )
        elif lifecycle.get("command") != expected_command:
            issues.append("release freeze lifecycle command must be make ai-close-work-item")
        if lifecycle.get("baseCommit") != source_tree:
            issues.append(
                "release freeze lifecycle baseCommit must match candidate source identity"
            )
        if lifecycle.get("worktreeClean") is not True:
            issues.append("release freeze lifecycle must record a clean worktree")
    if freeze.get("sourceTree") != source_tree:
        issues.append("release freeze sourceTree does not match candidate source tree")
    if freeze.get("archiveSha256") != actual_archive_sha:
        issues.append("release freeze archiveSha256 does not match regenerated archive")
    declared = release.get("releaseArchive", {}).get("sha256")
    if declared != actual_archive_sha:
        issues.append("release.json releaseArchive.sha256 does not match regenerated archive")
    if release_digests is not None and source_commit is not None:
        if release_digests.get("sourceCommit") != source_commit:
            issues.append("release-digests sourceCommit does not match candidate source commit")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-commit", default="HEAD")
    args = parser.parse_args()
    root = args.root.resolve()
    release = _load_object(root / "release.json", "release.json")
    release_state = _load_object(root / "release-state.json", "release-state.json")
    candidate = _load_object(root / "next-release.json", "next-release.json")
    freeze = _load_object(root / ".ai" / "cockpit" / "release-freeze.json", "release-freeze.json")
    release_digests = _load_object(
        root / ".ai" / "cockpit" / "release-digests.json", "release-digests.json"
    )
    try:
        source_commit = resolve_source_commit(root, args.source_commit)
        resolved_declared_source = resolve_release_identity_ref(
            root, release_digests.get("sourceCommit"), "release-digests sourceCommit"
        )
        resolved_tag_target = resolve_release_identity_ref(
            root, release_digests.get("tagTarget"), "release-digests tagTarget"
        )
        resolved_metadata_commit = resolve_release_identity_ref(
            root, release_digests.get("metadataCommit"), "release-digests metadataCommit"
        )
        resolved_freeze = dict(freeze)
        for field in ("sourceCommit", "tagTarget", "metadataCommit"):
            resolved_freeze[field] = resolve_release_identity_ref(
                root, freeze.get(field), f"freeze {field}"
            )
    except ReleasePreflightError as exc:
        print(f"release preflight blocked: {exc}", file=sys.stderr)
        return 1
    projection_issues = validate_release_projection(
        state=release_state, release=release, candidate=candidate
    )
    if projection_issues:
        print("release preflight blocked:", file=sys.stderr)
        for issue in projection_issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    comparable_digests = dict(release_digests)
    comparable_digests["sourceCommit"] = resolved_declared_source
    comparable_digests["tagTarget"] = resolved_tag_target
    comparable_digests["metadataCommit"] = resolved_metadata_commit
    actual = canonical_archive_sha(root, source_commit)
    source_tree = canonical_source_tree(root, source_commit)
    active = sorted(
        path.name.removesuffix(".contract.json")
        for path in (root / ".ai" / "work-items" / "active").glob("*.contract.json")
    )
    policy = root / ".ai" / "guards" / "governance_complexity_policy.yaml"
    archive_max = 0
    archive_enforcement = "error"
    enforcement_section = False
    for line in policy.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "enforcement:":
            enforcement_section = True
            continue
        if stripped.startswith("archiveGrowth:") and not enforcement_section:
            archive_max = int(stripped.split(":", 1)[1].strip())
        elif enforcement_section and stripped == "archiveGrowth: warning":
            archive_enforcement = "warning"
    archive_count = len(list((root / ".ai" / "work-items" / "archive").glob("**/*.contract.json")))
    issues = validate_release_preflight(
        release=release,
        freeze=freeze,
        release_digests=comparable_digests,
        source_commit=source_commit,
        actual_archive_sha=actual,
        source_tree=source_tree,
        active_work_items=active,
        archive_count=archive_count,
        archive_max=archive_max,
        archive_enforcement=archive_enforcement,
    )
    issues.extend(
        validate_release_identity(
            release=release,
            freeze=resolved_freeze,
            release_digests=comparable_digests,
            source_commit=source_commit,
            tag_target=comparable_digests.get("tagTarget", ""),
            metadata_commit=comparable_digests.get("metadataCommit", ""),
        )
    )
    if issues:
        print(
            "release preflight diagnostics: "
            + json.dumps(
                {
                    "head": resolve_source_commit(root, "HEAD"),
                    "sourceCommit": source_commit,
                    "sourceTree": source_tree,
                    "declaredSourceTree": freeze.get("sourceTree"),
                    "archiveSha256": actual,
                    "declaredArchiveSha256": freeze.get("archiveSha256"),
                    "declaredReleaseArchiveSha256": release.get("releaseArchive", {}).get("sha256"),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        print("release preflight blocked:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print(f"release preflight passed: source={source_commit} archive={actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
