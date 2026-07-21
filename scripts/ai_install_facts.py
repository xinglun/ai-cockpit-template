#!/usr/bin/env python3
"""Create and validate durable Installed Lifecycle installation facts."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FACT_DIR = Path(".ai/install")
FACT_NAMES = ("manifest.json", "version.json", "managed-regions.json", "rollback-baseline.json")
OWNERSHIPS = {"template", "project", "shared", "generated", "historical"}


class InstallFactsError(ValueError):
    """Raised when installation facts are missing, malformed, or inconsistent."""


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> str:
    payload = canonical_json(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return digest_bytes(payload)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InstallFactsError(f"invalid installation fact: {path}") from exc


def classify_path(relative: str) -> str:
    if relative.startswith(".ai/work-items/archive/"):
        return "historical"
    if relative.startswith(".ai/cockpit/") or relative.startswith(".ai/install/"):
        return "generated"
    if relative.startswith(".ai/guards/") or relative.startswith(".cursor/"):
        return "shared"
    if relative.startswith(".ai/project") or relative == ".ai/glossary.md":
        return "project"
    return "template"


def _source_commit(source: Path) -> str | None:
    try:
        import subprocess

        result = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def build_manifest(
    *, source: Path, target: Path, distribution_version: dict[str, Any]
) -> dict[str, Any]:
    files: list[dict[str, str]] = []
    for path in sorted(target.rglob("*")):
        if not path.is_file() or FACT_DIR.as_posix() in path.relative_to(target).as_posix():
            continue
        relative = path.relative_to(target).as_posix()
        if relative.startswith(".git/") or relative in {".gitignore"}:
            continue
        if relative.startswith(".ai/work-items/active/"):
            continue
        source_path = relative if (source / relative).is_file() else ""
        files.append(
            {
                "path": relative,
                "sourcePath": source_path,
                "ownership": classify_path(relative),
                "installedDigest": digest_file(path),
            }
        )
    installed_at = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    return {
        "schemaVersion": 1,
        "installationId": str(uuid.uuid4()),
        "installedAt": installed_at,
        "source": {
            "distributionVersion": distribution_version.get("distributionVersion"),
            "releaseVersion": distribution_version.get("releaseVersion"),
            "contractSchema": distribution_version.get("contractSchema"),
            "sourceCommit": _source_commit(source),
        },
        "files": files,
    }


def write_fact_bundle(
    *, source: Path, target: Path, distribution_version: dict[str, Any]
) -> dict[str, Any]:
    manifest = build_manifest(
        source=source, target=target, distribution_version=distribution_version
    )
    manifest_path = target / FACT_DIR / "manifest.json"
    manifest_hash = write_json(manifest_path, manifest)
    version = {
        "schemaVersion": 1,
        "installationId": manifest["installationId"],
        "installedAt": manifest["installedAt"],
        "distributionVersion": distribution_version.get("distributionVersion"),
        "releaseVersion": distribution_version.get("releaseVersion"),
        "contractSchema": distribution_version.get("contractSchema"),
        "sourceCommit": manifest["source"]["sourceCommit"],
        "manifestHash": manifest_hash,
        "runtimeState": "active",
    }
    regions = {
        "schemaVersion": 1,
        "installationId": manifest["installationId"],
        "regions": [
            {
                "path": item["path"],
                "ownership": item["ownership"],
                "region": "full-file",
                "installedDigest": item["installedDigest"],
            }
            for item in manifest["files"]
            if item["ownership"] == "shared"
        ],
    }
    baseline = {
        "schemaVersion": 1,
        "installationId": manifest["installationId"],
        "createdAt": manifest["installedAt"],
        "manifestHash": manifest_hash,
        "fileDigests": {item["path"]: item["installedDigest"] for item in manifest["files"]},
    }
    write_json(target / FACT_DIR / "version.json", version)
    write_json(target / FACT_DIR / "managed-regions.json", regions)
    write_json(target / FACT_DIR / "rollback-baseline.json", baseline)
    return validate_fact_bundle(target)


def validate_fact_bundle(root: Path) -> dict[str, Any]:
    paths = {name: root / FACT_DIR / name for name in FACT_NAMES}
    if any(not path.is_file() for path in paths.values()):
        missing = [name for name, path in paths.items() if not path.is_file()]
        raise InstallFactsError(f"missing installation facts: {', '.join(missing)}")
    manifest = read_json(paths["manifest.json"])
    version = read_json(paths["version.json"])
    regions = read_json(paths["managed-regions.json"])
    baseline = read_json(paths["rollback-baseline.json"])
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 1:
        raise InstallFactsError("manifest schema is unsupported")
    if not isinstance(manifest.get("installationId"), str) or not manifest["installationId"]:
        raise InstallFactsError("manifest installationId is missing")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise InstallFactsError("manifest files are missing")
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise InstallFactsError("manifest contains an invalid file entry")
        if item.get("ownership") not in OWNERSHIPS or not isinstance(
            item.get("installedDigest"), str
        ):
            raise InstallFactsError("manifest contains an invalid ownership or digest")
        path = root / item["path"]
        if not path.is_file() or digest_file(path) != item["installedDigest"]:
            raise InstallFactsError(f"installation fact digest mismatch: {item['path']}")
    expected_manifest_hash = digest_file(paths["manifest.json"])
    if not isinstance(version, dict) or version.get("schemaVersion") != 1:
        raise InstallFactsError("version fact schema is unsupported")
    if (
        version.get("installationId") != manifest["installationId"]
        or version.get("manifestHash") != expected_manifest_hash
    ):
        raise InstallFactsError("version fact is not bound to the manifest")
    if not isinstance(regions, dict) or regions.get("installationId") != manifest["installationId"]:
        raise InstallFactsError("managed-regions fact is not bound to the manifest")
    if (
        not isinstance(baseline, dict)
        or baseline.get("installationId") != manifest["installationId"]
    ):
        raise InstallFactsError("rollback baseline is not bound to the manifest")
    if baseline.get("fileDigests") != {item["path"]: item["installedDigest"] for item in files}:
        raise InstallFactsError("rollback baseline digests do not match the manifest")
    return {
        "manifest": manifest,
        "version": version,
        "managedRegions": regions,
        "rollbackBaseline": baseline,
    }
