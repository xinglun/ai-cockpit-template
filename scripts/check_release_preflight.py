#!/usr/bin/env python3
"""Fail-closed checks that must pass before expensive release CI starts."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class ReleasePreflightError(ValueError):
    """Raised when a release candidate is not frozen and source-bound."""


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


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleasePreflightError(f"{label} is missing or invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleasePreflightError(f"{label} must be a JSON object")
    return value


def _canonical_tar(root: Path, source_commit: str) -> bytes:
    """Create the deterministic source tar; Git export-ignore removes metadata."""
    return subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "archive",
            "--format=tar",
            "--mtime=1970-01-01 00:00:00",
            "--prefix=ai-cockpit/",
            f"{source_commit}^{{tree}}",
        ],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def canonical_source_tree(root: Path, source_commit: str) -> str:
    """Return a normalized source identity that excludes self-referential metadata."""
    return hashlib.sha256(_canonical_tar(root, source_commit)).hexdigest()


def canonical_archive_sha(root: Path, source_commit: str) -> str:
    """Create the same deterministic gzip stream as the release workflow."""
    tar = _canonical_tar(root, source_commit)
    digest = hashlib.sha256()
    compressor = gzip.GzipFile(  # type: ignore[call-overload]
        fileobj=_HashWriter(digest), mode="wb", compresslevel=9, mtime=0
    )
    compressor.write(tar)
    compressor.close()
    return digest.hexdigest()


class _HashWriter:
    def __init__(self, digest: Any) -> None:
        self.digest = digest

    def write(self, data: bytes) -> int:
        self.digest.update(data)
        return len(data)


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
) -> list[str]:
    issues: list[str] = []
    if active_work_items:
        issues.append(f"active Work Items remain: {', '.join(active_work_items)}")
    if archive_count > archive_max:
        issues.append(f"archiveGrowth={archive_count} exceeds configured maximum {archive_max}")
    if freeze.get("state") != "frozen":
        issues.append("release-freeze.json state must be frozen")
    lifecycle = freeze.get("lifecycle")
    if not isinstance(lifecycle, dict) or lifecycle.get("state") != "closed_and_synchronized":
        issues.append(
            "release freeze lifecycle must be generated after ai-close-work-item and base synchronization"
        )
    else:
        if lifecycle.get("command") != "make ai-close-work-item":
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
    freeze = _load_object(root / ".ai" / "cockpit" / "release-freeze.json", "release-freeze.json")
    release_digests = _load_object(
        root / ".ai" / "cockpit" / "release-digests.json", "release-digests.json"
    )
    try:
        source_commit = resolve_source_commit(root, args.source_commit)
        declared_source = release_digests.get("sourceCommit")
        if not isinstance(declared_source, str) or not declared_source:
            raise ReleasePreflightError("release-digests sourceCommit is missing or invalid")
        resolved_declared_source = resolve_source_commit(root, declared_source)
    except ReleasePreflightError as exc:
        print(f"release preflight blocked: {exc}", file=sys.stderr)
        return 1
    comparable_digests = dict(release_digests)
    comparable_digests["sourceCommit"] = resolved_declared_source
    actual = canonical_archive_sha(root, source_commit)
    source_tree = canonical_source_tree(root, source_commit)
    active = sorted(
        path.name.removesuffix(".contract.json")
        for path in (root / ".ai" / "work-items" / "active").glob("*.contract.json")
    )
    policy = root / ".ai" / "guards" / "governance_complexity_policy.yaml"
    archive_max = 0
    for line in policy.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("archiveGrowth:"):
            archive_max = int(line.split(":", 1)[1].strip())
            break
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
    )
    if issues:
        print("release preflight blocked:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print(f"release preflight passed: source={source_commit} archive={actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
