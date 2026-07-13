#!/usr/bin/env python3
"""Validate template supply-chain evidence: SBOM, provenance, secrets, and vulnerabilities."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SBOM_BASELINE = ROOT / ".ai" / "cockpit" / "sbom.json"
PROVENANCE_BASELINE = ROOT / ".ai" / "cockpit" / "provenance.json"
WORKFLOW_DIR = ROOT / ".github" / "workflows"
LOCK_FILE = ROOT / "requirements-dev.lock"
RELEASE_JSON = ROOT / "release.json"
INSTALLER = ROOT / "install.sh"
TEST_PRIVATE_KEY_FIXTURE = Path("tests/test_core_gates.py")


SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")),
]
PRIVATE_KEY_BEGIN = re.compile(r"-----BEGIN ([^-]+)-----")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a JSON object")
    return data


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def clean_git_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key != "AI_BASE_COMMIT"
    }


def git_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        env=clean_git_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")
    return [ROOT / item for item in result.stdout.split("\0") if item]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def parse_requirements_lock(path: Path) -> list[dict[str, str]]:
    components: list[dict[str, str]] = []
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, version = line.split("==", 1)
        components.append({"type": "library", "name": name, "version": version})
    return components


def parse_workflow_actions(root: Path) -> list[dict[str, str]]:
    components: list[dict[str, str]] = []
    for path in sorted(root.glob("*.y*ml")):
        text = read_text(path)
        for match in re.finditer(
            r"^\s*(?:-\s*)?uses:\s*([^@\s]+)@([^\s]+)\s*$", text, re.MULTILINE
        ):
            components.append({"type": "action", "name": match.group(1), "version": match.group(2)})
    return components


def release_tag() -> str:
    release = load_json(RELEASE_JSON)
    tag = release.get("releaseTag")
    if not isinstance(tag, str) or not tag:
        raise ValueError("release.json releaseTag is missing or invalid")
    return tag


def release_commit_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"{release_tag()}^{{commit}}"],
        cwd=ROOT,
        env=clean_git_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git rev-parse failed")
    return result.stdout.strip()


def build_sbom() -> dict[str, Any]:
    components = [*parse_requirements_lock(LOCK_FILE), *parse_workflow_actions(WORKFLOW_DIR)]
    components = sorted(components, key=lambda item: (item["type"], item["name"], item["version"]))
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "metadata": {
            "component": {
                "type": "application",
                "name": "ai-cockpit-template",
                "version": release_commit_sha(),
            }
        },
        "components": components,
    }


def build_provenance(sbom: dict[str, Any]) -> dict[str, Any]:
    release = load_json(RELEASE_JSON)
    installer_text = read_text(INSTALLER)
    return {
        "builder": "ai-cockpit-template",
        "commitSha": release_commit_sha(),
        "sbomDigest": sha256_text(json.dumps(sbom, sort_keys=True, ensure_ascii=False)),
        "requirementsLockDigest": sha256_text(read_text(LOCK_FILE)),
        "releaseTag": release.get("releaseTag"),
        "installerDigest": sha256_text(installer_text),
    }


def compare_or_write(path: Path, data: dict[str, Any], *, write: bool) -> list[str]:
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return []
    if not path.exists():
        return [f"{path.relative_to(ROOT)} is missing"]
    current = json.loads(path.read_text(encoding="utf-8"))
    if current != data:
        return [f"{path.relative_to(ROOT)} differs from the computed supply-chain evidence"]
    return []


def scan_secrets() -> list[str]:
    issues: list[str] = []
    for path in git_files():
        if not path.is_file():
            continue
        if path.suffix in {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".pdf",
            ".zip",
            ".gz",
            ".tgz",
            ".jar",
            ".class",
        }:
            continue
        try:
            text = read_text(path)
        except OSError:
            continue
        for match in PRIVATE_KEY_BEGIN.finditer(text):
            label = "private_key"
            key_type = match.group(1)
            end_marker = f"-----END {key_type}-----"
            if text.find(end_marker, match.end()) == -1:
                label = "private_key_fragment"
            if label == "private_key" and path.relative_to(ROOT) == TEST_PRIVATE_KEY_FIXTURE:
                continue
            issues.append(f"{path.relative_to(ROOT)}:{label}:{match.start() + 1}")
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                issues.append(f"{path.relative_to(ROOT)}:{label}:{match.start() + 1}")
    return sorted(set(issues))


def scan_vulnerabilities() -> list[str]:
    """Run pip-audit against the locked development dependencies."""
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "-r", str(LOCK_FILE), "--format=json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError(result.stderr.strip() or "pip-audit failed")

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("pip-audit returned invalid JSON") from exc

    issues: list[str] = []
    for dependency in payload.get("dependencies", []):
        if not isinstance(dependency, dict):
            continue
        name = dependency.get("name", "unknown")
        version = dependency.get("version", "unknown")
        for vuln in dependency.get("vulns", []):
            if not isinstance(vuln, dict):
                continue
            vuln_id = vuln.get("id", "unknown")
            fix_versions = vuln.get("fix_versions", [])
            fix_suffix = f" fix={','.join(fix_versions)}" if fix_versions else ""
            issues.append(f"{name}=={version}:{vuln_id}{fix_suffix}")

    if result.returncode == 0 and issues:
        raise RuntimeError("pip-audit reported vulnerabilities without a failing exit code")
    return sorted(issues)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("sbom", "provenance"):
        cmd = sub.add_parser(name)
        cmd.add_argument(
            "--write", action="store_true", help="Write the computed evidence to the baseline file."
        )
    sub.add_parser("secrets")
    sub.add_parser("vulnerabilities")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "sbom":
            issues = compare_or_write(SBOM_BASELINE, build_sbom(), write=bool(args.write))
        elif args.command == "provenance":
            sbom = build_sbom()
            issues = compare_or_write(
                PROVENANCE_BASELINE, build_provenance(sbom), write=bool(args.write)
            )
        elif args.command == "vulnerabilities":
            issues = scan_vulnerabilities()
        else:
            issues = scan_secrets()
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print(f"{args.command} supply-chain check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
