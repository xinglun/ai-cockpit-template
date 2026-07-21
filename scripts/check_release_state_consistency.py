#!/usr/bin/env python3
"""Validate canonical release state against published and candidate metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


STATES = {"development", "candidate_prepared", "candidate_verified", "release_published"}
TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def load_object(path: Path, label: str, issues: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"{label} is not readable JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        issues.append(f"{label} must contain a JSON object")
        return {}
    return value


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def check_repository(root: Path) -> list[str]:
    issues: list[str] = []
    state_path = root / "release-state.json"
    published_path = root / "release.json"
    candidate_path = root / "next-release.json"
    state = load_object(state_path, "release-state.json", issues)
    published = load_object(published_path, "release.json", issues)
    candidate = load_object(candidate_path, "next-release.json", issues)

    state_name = state.get("state")
    if state_name not in STATES:
        issues.append(f"release-state.json state must be one of {sorted(STATES)}")
    state_tag = state.get("releaseTag")
    if not isinstance(state_tag, str) or not TAG_PATTERN.fullmatch(state_tag):
        issues.append("release-state.json releaseTag must be a semantic version tag")
    source_commit = state.get("sourceCommit")
    if not isinstance(source_commit, str) or not SHA_PATTERN.fullmatch(source_commit):
        issues.append("release-state.json sourceCommit must be a 40-character lowercase SHA")
    previous = state.get("previousRelease")
    if not isinstance(previous, str) or not TAG_PATTERN.fullmatch(previous):
        issues.append("release-state.json previousRelease must be a semantic version tag")
    if "evidenceBundleDigest" not in state:
        issues.append("release-state.json evidenceBundleDigest is required")

    published_tag = published.get("releaseTag")
    candidate_tag = candidate.get("releaseTag")
    if state_name in {"candidate_prepared", "candidate_verified"} and state_tag != candidate_tag:
        issues.append(
            f"canonical candidate releaseTag {state_tag!r} disagrees with next-release.json {candidate_tag!r}"
        )
    if state_name == "release_published" and state_tag != published_tag:
        issues.append(
            f"canonical published releaseTag {state_tag!r} disagrees with release.json {published_tag!r}"
        )
    if previous != published_tag:
        issues.append(
            f"release-state.json previousRelease {previous!r} does not equal published release {published_tag!r}"
        )
    if published_tag == candidate_tag:
        issues.append("published and candidate tags must be distinct")
    if candidate.get("basedOnReleaseTag") != published_tag:
        issues.append("next-release.json basedOnReleaseTag must equal release.json releaseTag")
    if candidate.get("releaseState") != "candidate" or candidate.get("published") is not False:
        issues.append("next-release.json must remain an unpublished candidate")

    digests = state.get("metadataDigests")
    if not isinstance(digests, dict):
        issues.append("release-state.json metadataDigests must reference legacy metadata files")
    else:
        for key, path in (("published", published_path), ("candidate", candidate_path)):
            expected = digests.get(key)
            actual = sha256_file(path)
            if not isinstance(expected, str) or not DIGEST_PATTERN.fullmatch(expected):
                issues.append(
                    f"release-state.json metadata digest {key} must be a SHA-256 hex digest"
                )
            elif actual is None or expected != actual:
                issues.append(
                    f"release-state.json metadata digest {key} does not match {path.name}"
                )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    issues = check_repository(args.root)
    if issues:
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("release state consistency check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
