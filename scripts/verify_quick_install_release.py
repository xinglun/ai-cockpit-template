#!/usr/bin/env python3
"""Verify the immutable release contract used by anonymous Quick Install."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


class ReleaseVerificationError(ValueError):
    """Raised when a Quick Install release contract is incomplete or mismatched."""


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    )
    if result.returncode != 0:
        raise ReleaseVerificationError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def load_release_metadata(root: Path) -> dict[str, Any]:
    path = root / "release.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseVerificationError(f"release.json is unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseVerificationError("release.json must contain an object")
    if (root / "next-release.json").is_file():
        # Presence is allowed; the default path must never read its contents.
        pass
    return value


def declared_archive(metadata: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    capabilities = metadata.get("capabilities")
    capability = (
        capabilities.get("sha256ArchiveVerification") if isinstance(capabilities, dict) else None
    )
    if isinstance(capability, dict):
        supported = capability.get("supported") is True
        verified = capability.get("verified") is True
    else:
        supported = capability is True
        verified = capability is True
    archive = metadata.get("releaseArchive")
    if not isinstance(archive, dict):
        raise ReleaseVerificationError("release.json releaseArchive evidence is missing")
    if not supported:
        raise ReleaseVerificationError("release.json does not declare archive verification support")
    if not verified:
        raise ReleaseVerificationError("release.json archive verification is not verified")
    return archive, verified


def verify_release(
    root: Path,
    *,
    ref: str,
    asset_url: str | None = None,
    expected_archive_sha256: str | None = None,
    timeout: int = 30,
) -> dict[str, str]:
    metadata = load_release_metadata(root)
    if metadata.get("releaseTag") != ref:
        raise ReleaseVerificationError(
            f"release tag mismatch (expected={ref!r}, declared={metadata.get('releaseTag')!r})"
        )
    try:
        tag_commit = run_git(root, "rev-parse", f"refs/tags/{ref}^{{commit}}")
    except ReleaseVerificationError as exc:
        raise ReleaseVerificationError(f"release tag {ref!r} is unavailable locally") from exc
    declared_source = metadata.get("sourceCommit")
    if declared_source is not None and (
        not isinstance(declared_source, str) or not COMMIT.fullmatch(declared_source)
    ):
        raise ReleaseVerificationError("release.json sourceCommit is invalid")
    if isinstance(declared_source, str) and declared_source != tag_commit:
        raise ReleaseVerificationError(
            f"declared source commit mismatch (expected={tag_commit}, actual={declared_source})"
        )
    source_commit = tag_commit
    installer = root / "install.sh"
    expected_installer = metadata.get("installerDigest")
    if not isinstance(expected_installer, str) or not SHA256.fullmatch(expected_installer):
        raise ReleaseVerificationError("release.json installerDigest is missing or invalid")
    actual_installer = digest_file(installer)
    if actual_installer != expected_installer:
        raise ReleaseVerificationError(
            f"installer digest mismatch (expected={expected_installer}, actual={actual_installer})"
        )
    archive, _verified = declared_archive(metadata)
    archive_source = archive.get("sourceCommit")
    if archive_source is not None and archive_source != source_commit:
        raise ReleaseVerificationError("releaseArchive.sourceCommit differs from tag target")
    asset_name = archive.get("assetName")
    archive_sha256 = archive.get("sha256")
    declared_url = archive.get("url")
    if not isinstance(asset_name, str) or not asset_name or "/" in asset_name or "\\" in asset_name:
        raise ReleaseVerificationError("releaseArchive.assetName is missing or unsafe")
    if not isinstance(archive_sha256, str) or not SHA256.fullmatch(archive_sha256):
        raise ReleaseVerificationError("releaseArchive.sha256 is missing or invalid")
    if not isinstance(declared_url, str) or not declared_url:
        raise ReleaseVerificationError("releaseArchive.url is missing")
    if expected_archive_sha256 and expected_archive_sha256 != archive_sha256:
        raise ReleaseVerificationError("caller archive SHA256 assertion differs from release.json")
    url = asset_url or declared_url
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme in {"http", "https"} and Path(parsed.path).name != asset_name:
        raise ReleaseVerificationError("release archive URL does not name the declared asset")
    request = urllib.request.Request(url, headers={"User-Agent": "ai-cockpit-quick-install"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            payload = response.read()
    except (OSError, urllib.error.URLError) as exc:
        raise ReleaseVerificationError(f"release archive asset is unavailable: {exc}") from exc
    actual_archive = digest_bytes(payload)
    if actual_archive != archive_sha256:
        raise ReleaseVerificationError(
            f"archive SHA256 mismatch (expected={archive_sha256}, actual={actual_archive})"
        )
    return {
        "releaseTag": ref,
        "sourceCommit": source_commit,
        "installerDigest": actual_installer,
        "assetName": asset_name,
        "archiveSha256": actual_archive,
        "assetUrl": url,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--ref", required=True)
    parser.add_argument("--asset-url")
    parser.add_argument("--expected-archive-sha256")
    args = parser.parse_args()
    try:
        evidence = verify_release(
            args.root.resolve(),
            ref=args.ref,
            asset_url=args.asset_url,
            expected_archive_sha256=args.expected_archive_sha256,
        )
    except ReleaseVerificationError as exc:
        print(f"ERROR: Quick Install release verification failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
