#!/usr/bin/env python3
"""Validate template supply-chain evidence: SBOM, provenance, secrets, and vulnerabilities."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import uuid
from datetime import datetime, timezone
from typing import Any

from cyclonedx.model import ExternalReference, ExternalReferenceType, HashAlgorithm, HashType, XsUri
from cyclonedx.model.bom import Bom, BomMetaData
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.tool import Tool
from cyclonedx.output.json import JsonV1Dot5
from packageurl import PackageURL


ROOT = Path(__file__).resolve().parents[1]
SBOM_BASELINE = ROOT / ".ai" / "cockpit" / "sbom.json"
PROVENANCE_BASELINE = ROOT / ".ai" / "cockpit" / "provenance.json"
RELEASE_DIGESTS_BASELINE = ROOT / ".ai" / "cockpit" / "release-digests.json"
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


def normalize_package_name(name: str) -> str:
    base_name = name.split("[", 1)[0]
    return re.sub(r"[-_.]+", "-", base_name).lower()


def parse_requirements_lock(path: Path) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_via_block = False
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "==" not in line:
            if current and "--hash=sha256:" in line:
                current["hashes"].extend(re.findall(r"--hash=sha256:([0-9a-fA-F]+)", line))
            if current and line.startswith("# via"):
                via = line.removeprefix("# via").strip()
                if via:
                    current["via"].append(via)
                in_via_block = True
            elif current and in_via_block and line.startswith("#   "):
                current["via"].append(line.removeprefix("#   ").strip())
            elif line and not line.startswith("#   "):
                in_via_block = False
            continue
        name, version = line.split("==", 1)
        current = {
            "type": "library",
            "name": name.strip(),
            "version": version.rstrip("\\").strip(),
            "hashes": re.findall(r"--hash=sha256:([0-9a-fA-F]+)", line),
            "via": [],
        }
        components.append(current)
        in_via_block = False
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


def lock_semantics(path: Path) -> dict[str, Any]:
    """Describe direct, transitive, version, and artifact-hash lock coverage."""
    entries: list[dict[str, bool]] = []
    current: dict[str, bool] | None = None
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "==" in line and not line.startswith("#"):
            current = {"hashed": False, "direct": False, "hasVia": False}
            entries.append(current)
            continue
        if current is None:
            continue
        if "--hash=sha256:" in line:
            current["hashed"] = True
        if line.startswith("# via") or line.startswith("#   "):
            current["hasVia"] = True
            if "requirements-dev.in" in line:
                current["direct"] = True

    # Older hand-maintained locks had no pip-compile attribution. Preserve their
    # direct-only interpretation while generated locks expose transitive edges.
    if entries and not any(entry["hasVia"] for entry in entries):
        for entry in entries:
            entry["direct"] = True

    direct = sum(entry["direct"] for entry in entries)
    transitive = len(entries) - direct
    return {
        "directDependencies": direct,
        "lockedDependencies": len(entries),
        "transitiveDependencies": {
            "status": "generated" if transitive else "not_generated",
            "count": transitive,
            "source": "requirements-dev.lock",
        },
        "versionPins": bool(entries),
        "hashPins": bool(entries) and all(entry["hashed"] for entry in entries),
        "requireHashesCompatible": bool(entries) and all(entry["hashed"] for entry in entries),
    }


def release_tag() -> str:
    release = load_json(RELEASE_JSON)
    tag = release.get("releaseTag")
    if not isinstance(tag, str) or not tag:
        raise ValueError("release.json releaseTag is missing or invalid")
    return tag


def source_commit_sha(explicit: str | None = None) -> str:
    """Resolve evidence identity from explicit input or the immutable release tag.

    A committed provenance baseline must never become the source of a later
    provenance identity: doing so lets old evidence silently attest a new
    release. Final release evidence supplies the immutable source commit
    explicitly; local generation falls back to the release tag only.
    """
    requested = (explicit or os.environ.get("SUPPLY_CHAIN_SOURCE_COMMIT", "")).strip()
    tag = release_tag()
    revision = requested or tag
    result = subprocess.run(
        ["git", "rev-parse", f"{revision}^{{commit}}"],
        cwd=ROOT,
        env=clean_git_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 and not requested:
        # Before the new release tag exists (for example in PR validation),
        # prefer a concrete identity already written by finalizer. This keeps
        # all downstream evidence on the same source/tag/metadata tuple after
        # freeze finalization, instead of silently reverting to old
        # provenance. Historical candidate provenance remains the fallback
        # only when no finalized identity exists.
        finalized = load_json(RELEASE_DIGESTS_BASELINE)
        finalized_source = finalized.get("sourceCommit")
        finalized_identity = (
            isinstance(finalized_source, str)
            and bool(finalized_source)
            and finalized.get("releaseTag") == tag
            and finalized.get("tagTarget") == finalized_source
            and finalized.get("metadataCommit") == finalized_source
        )
        if finalized_identity:
            revision = str(finalized_source)
        else:
            # Retain the previously published evidence identity while a
            # pending publication PR carries the new release metadata. The
            # immutable release workflow will replace this candidate baseline
            # with source-bound assets after the tag is created.
            next_release = load_json(ROOT / "next-release.json")
            baseline = load_json(PROVENANCE_BASELINE)
            pending_publication = (
                next_release.get("releaseState") == "candidate"
                and next_release.get("published") is False
                and next_release.get("releaseTag") != tag
                and next_release.get("basedOnReleaseTag") == tag
                and baseline.get("releaseTag") == tag
                and isinstance(baseline.get("commitSha"), str)
            )
            revision = baseline["commitSha"] if pending_publication else "HEAD"
        result = subprocess.run(
            ["git", "rev-parse", revision],
            cwd=ROOT,
            env=clean_git_environment(),
            text=True,
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git rev-parse failed")
    return result.stdout.strip()


def release_commit_sha() -> str:
    """Backward-compatible release evidence identity resolver."""
    return source_commit_sha()


def build_sbom(source_commit: str | None = None) -> dict[str, Any]:
    lock_components = parse_requirements_lock(LOCK_FILE)
    action_components = parse_workflow_actions(WORKFLOW_DIR)
    semantics = lock_semantics(LOCK_FILE)
    resolved_commit = source_commit_sha(source_commit)
    model_components: dict[str, Component] = {}
    for item in [*lock_components, *action_components]:
        if item["type"] == "library":
            purl = PackageURL(
                type="pypi", name=normalize_package_name(item["name"]), version=item["version"]
            )
            component = Component(
                name=item["name"],
                version=item["version"],
                type=ComponentType.LIBRARY,
                bom_ref=str(purl),
                purl=purl,
                hashes=[
                    HashType(alg=HashAlgorithm.SHA_256, content=value) for value in item["hashes"]
                ],
                external_references=[
                    ExternalReference(
                        type=ExternalReferenceType.DISTRIBUTION, url=XsUri(component_url)
                    )
                    for component_url in [
                        f"https://pypi.org/project/{item['name']}/{item['version']}/"
                    ]
                ],
            )
        else:
            namespace, _, name = item["name"].partition("/")
            purl = PackageURL(
                type="github", namespace=namespace, name=name, version=item["version"]
            )
            component = Component(
                name=item["name"],
                version=item["version"],
                type=ComponentType.FRAMEWORK,
                bom_ref=str(purl),
                purl=purl,
                external_references=[
                    ExternalReference(
                        type=ExternalReferenceType.WEBSITE,
                        url=XsUri(f"https://github.com/{item['name']}"),
                    )
                ],
            )
        model_components[str(component.bom_ref)] = component

    app = Component(
        name="ai-cockpit-template",
        version=resolved_commit,
        type=ComponentType.APPLICATION,
        bom_ref="ai-cockpit-template",
    )
    bom = Bom(
        components=model_components.values(),
        serial_number=uuid.uuid5(uuid.NAMESPACE_URL, f"ai-cockpit-template:{resolved_commit}"),
        metadata=BomMetaData(
            component=app,
            timestamp=datetime(1970, 1, 1, tzinfo=timezone.utc),
            tools=[Tool(name="check_supply_chain", version=resolved_commit)],
        ),
    )
    direct_components = []
    for item in lock_components:
        component = model_components[
            str(
                PackageURL(
                    type="pypi", name=normalize_package_name(item["name"]), version=item["version"]
                )
            )
        ]
        if any(via.startswith("-r ") for via in item["via"]):
            direct_components.append(component)
        bom.register_dependency(component, [])
    for item in lock_components:
        for via in item["via"]:
            via_name = via.removeprefix("-r ").strip()
            if via_name in {candidate["name"] for candidate in lock_components}:
                via_component = model_components[
                    str(
                        PackageURL(
                            type="pypi",
                            name=normalize_package_name(via_name),
                            version=next(
                                candidate["version"]
                                for candidate in lock_components
                                if candidate["name"] == via_name
                            ),
                        )
                    )
                ]
                child_component = model_components[
                    str(
                        PackageURL(
                            type="pypi",
                            name=normalize_package_name(item["name"]),
                            version=item["version"],
                        )
                    )
                ]
                bom.register_dependency(via_component, [child_component])
    bom.register_dependency(app, direct_components)
    document = json.loads(JsonV1Dot5(bom).output_as_string())
    document["metadata"]["supplyChainCoverage"] = {
        "workflowActions": len(action_components),
        "lockedDirectDependencies": semantics["directDependencies"],
        "lockedDependencies": len(lock_components),
        "lockSemantics": semantics,
    }
    return document


def build_provenance(sbom: dict[str, Any], source_commit: str | None = None) -> dict[str, Any]:
    release = load_json(RELEASE_JSON)
    installer_text = read_text(INSTALLER)
    return {
        "builder": "ai-cockpit-template",
        "commitSha": source_commit_sha(source_commit),
        "sbomDigest": sha256_text(json.dumps(sbom, sort_keys=True, ensure_ascii=False)),
        "requirementsLockDigest": sha256_text(read_text(LOCK_FILE)),
        "releaseTag": release.get("releaseTag"),
        "installerDigest": sha256_text(installer_text),
    }


def build_release_digests(
    sbom: dict[str, Any],
    provenance: dict[str, Any],
    correlation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = {
        "format": "ai-cockpit-release-digests",
        "version": 1,
        "sourceCommit": provenance["commitSha"],
        # The finalizer binds the tag target and metadata commit to the same
        # concrete source commit.  Generate the complete tuple here so the
        # candidate baseline and final release evidence share one identity
        # model instead of disagreeing after freeze finalization.
        "tagTarget": provenance["commitSha"],
        "metadataCommit": provenance["commitSha"],
        "releaseTag": provenance["releaseTag"],
        "artifacts": {
            "requirements-dev.lock": sha256_text(read_text(LOCK_FILE)),
            ".ai/cockpit/sbom.json": sha256_text(
                json.dumps(sbom, sort_keys=True, ensure_ascii=False)
            ),
            ".ai/cockpit/provenance.json": sha256_text(
                json.dumps(provenance, sort_keys=True, ensure_ascii=False)
            ),
            "install.sh": sha256_text(read_text(INSTALLER)),
            "release.json": sha256_text(read_text(RELEASE_JSON)),
        },
    }
    if correlation is not None:
        manifest["correlation"] = correlation
    return manifest


def write_release_assets(
    output_dir: Path,
    source_commit: str,
    *,
    workflow_run_id: str | None = None,
    workflow_run_sha: str | None = None,
    release_tag: str | None = None,
) -> None:
    """Generate final release evidence outside the committed candidate baselines."""
    resolved_commit = source_commit_sha(source_commit)
    sbom = build_sbom(resolved_commit)
    provenance = build_provenance(sbom, resolved_commit)
    if provenance["commitSha"] != resolved_commit:
        raise RuntimeError("generated provenance commitSha does not match source commit")
    digests = build_release_digests(sbom, provenance)
    if workflow_run_id is not None or workflow_run_sha is not None or release_tag is not None:
        correlation = {
            "format": "ai-cockpit-release-correlation",
            "version": 1,
            "workflowRunId": workflow_run_id or "",
            "workflowRunSha": workflow_run_sha or "",
            "sourceCommit": resolved_commit,
            "releaseTag": release_tag or provenance["releaseTag"],
            "artifactDigests": {
                "sbom.json": sha256_text(json.dumps(sbom, sort_keys=True, ensure_ascii=False)),
                "provenance.json": sha256_text(
                    json.dumps(provenance, sort_keys=True, ensure_ascii=False)
                ),
            },
        }
        digests["correlation"] = correlation
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "sbom": output_dir / "sbom.json",
        "provenance": output_dir / "provenance.json",
        "releaseDigests": output_dir / "release-digests.json",
    }
    paths["sbom"].write_text(json.dumps(sbom, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    paths["provenance"].write_text(
        json.dumps(provenance, sort_keys=True, ensure_ascii=False), encoding="utf-8"
    )
    paths["releaseDigests"].write_text(
        json.dumps(digests, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def map_vulnerabilities_to_sbom(payload: dict[str, Any], sbom: dict[str, Any]) -> list[str]:
    components = {
        (normalize_package_name(component["name"]), component["version"]): component["bom-ref"]
        for component in sbom.get("components", [])
        if component.get("type") == "library" and component.get("purl", "").startswith("pkg:pypi/")
    }
    issues: list[str] = []
    for dependency in payload.get("dependencies", []):
        if not isinstance(dependency, dict):
            continue
        name = str(dependency.get("name", "unknown"))
        version = str(dependency.get("version", "unknown"))
        vulns = dependency.get("vulns", [])
        if not vulns:
            continue
        bom_ref = components.get((normalize_package_name(name), version))
        if not bom_ref:
            raise ValueError(
                f"pip-audit dependency cannot be mapped to SBOM component: {name}=={version}"
            )
        for vuln in vulns:
            if not isinstance(vuln, dict):
                continue
            vuln_id = vuln.get("id", "unknown")
            fix_versions = vuln.get("fix_versions", [])
            fix_suffix = f" fix={','.join(fix_versions)}" if fix_versions else ""
            issues.append(f"{bom_ref}:{vuln_id}{fix_suffix}")
    return sorted(issues)


def compare_or_write(path: Path, data: dict[str, Any], *, write: bool) -> list[str]:
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return []
    if not path.exists():
        return [f"{path.relative_to(ROOT)} is missing"]
    current = json.loads(path.read_text(encoding="utf-8"))
    expected = deepcopy(data)
    # Candidate baselines are committed before the immutable release tag exists.
    # Their volatile source identity is finalized in release-assets by release.yml;
    # compare dependency/action evidence here while retaining exact identity checks
    # for generated release assets.
    if path == SBOM_BASELINE:
        current.get("metadata", {}).get("component", {}).pop("version", None)
        expected.get("metadata", {}).get("component", {}).pop("version", None)
        for payload in (current, expected):
            payload.pop("serialNumber", None)
            tools = payload.get("metadata", {}).get("tools", [])
            for tool in tools:
                if tool.get("name") == "check_supply_chain":
                    tool.pop("version", None)
    elif path == PROVENANCE_BASELINE:
        current.pop("commitSha", None)
        expected.pop("commitSha", None)
        current.pop("sbomDigest", None)
        expected.pop("sbomDigest", None)
    elif path == RELEASE_DIGESTS_BASELINE:
        current.pop("sourceCommit", None)
        expected.pop("sourceCommit", None)
        # The committed candidate manifest is necessarily created before its
        # immutable release commit exists.  SBOM/provenance identities (and
        # their manifest hashes) therefore change with each candidate commit;
        # those two baseline files are compared separately above.  Keep the
        # manifest check focused on the stable release contract and exact
        # hashes for the remaining artifacts.  release-assets performs the
        # exact all-artifact check for the published tag.
        for payload in (current, expected):
            artifacts = payload.get("artifacts", {})
            artifacts.pop(".ai/cockpit/sbom.json", None)
            artifacts.pop(".ai/cockpit/provenance.json", None)
    if current != expected:
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

    issues = map_vulnerabilities_to_sbom(payload, build_sbom())

    if result.returncode == 0 and issues:
        raise RuntimeError("pip-audit reported vulnerabilities without a failing exit code")
    return sorted(issues)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("sbom", "provenance", "release"):
        cmd = sub.add_parser(name)
        cmd.add_argument(
            "--write", action="store_true", help="Write the computed evidence to the baseline file."
        )
        cmd.add_argument("--source-commit", default=None)
    assets = sub.add_parser(
        "release-assets",
        help="Generate final source-bound evidence outside committed candidate baselines.",
    )
    assets.add_argument("--source-commit", required=True)
    assets.add_argument("--output-dir", required=True, type=Path)
    assets.add_argument("--workflow-run-id")
    assets.add_argument("--workflow-run-sha")
    assets.add_argument("--release-tag")
    sub.add_parser("secrets")
    sub.add_parser("vulnerabilities")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "sbom":
            issues = compare_or_write(
                SBOM_BASELINE, build_sbom(args.source_commit), write=bool(args.write)
            )
        elif args.command == "provenance":
            sbom = build_sbom(args.source_commit)
            issues = compare_or_write(
                PROVENANCE_BASELINE,
                build_provenance(sbom, args.source_commit),
                write=bool(args.write),
            )
        elif args.command == "release":
            sbom = build_sbom(args.source_commit)
            provenance = build_provenance(sbom, args.source_commit)
            issues = compare_or_write(
                RELEASE_DIGESTS_BASELINE,
                build_release_digests(sbom, provenance),
                write=bool(args.write),
            )
        elif args.command == "release-assets":
            write_release_assets(
                args.output_dir,
                args.source_commit,
                workflow_run_id=args.workflow_run_id,
                workflow_run_sha=args.workflow_run_sha,
                release_tag=args.release_tag,
            )
            issues = []
        elif args.command == "vulnerabilities":
            issues = scan_vulnerabilities()
        else:
            issues = scan_secrets()
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if issues:
        print(f"supply-chain check failed: {len(issues)} issue(s)", file=sys.stderr)
        return 1
    print(f"{args.command} supply-chain check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
