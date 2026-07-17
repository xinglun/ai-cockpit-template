#!/usr/bin/env python3
"""Verify the documented release tag against its public installer behavior."""

from __future__ import annotations

import io
import json
import os
import hashlib
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release.json"
CANONICAL_REPOSITORY = "spirex-ds-dev/ai-cockpit-template"
PUBLIC_REPOSITORY = os.environ.get(
    "AI_COCKPIT_TEMPLATE_PUBLIC_REPOSITORY",
    f"https://github.com/{CANONICAL_REPOSITORY}.git",
)
SUPPLY_CHAIN_FILES = {
    "requirementsLockDigest": ROOT / "requirements-dev.lock",
    "sbomDigest": ROOT / ".ai" / "cockpit" / "sbom.json",
    "provenanceDigest": ROOT / ".ai" / "cockpit" / "provenance.json",
}
PUBLIC_ASSET_ARTIFACTS = {
    "sbom.json": ".ai/cockpit/sbom.json",
    "provenance.json": ".ai/cockpit/provenance.json",
    "release-digests.json": ".ai/cockpit/release-digests.json",
}
REQUIRED_MANIFEST_ARTIFACTS = {
    "requirements-dev.lock",
    ".ai/cockpit/sbom.json",
    ".ai/cockpit/provenance.json",
    "install.sh",
    "release.json",
}


def clean_git_environment() -> dict[str, str]:
    """Return an environment with no ambient Git repository or baseline overrides."""
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key != "AI_BASE_COMMIT"
    }


def clone_git_environment() -> dict[str, str]:
    """Return an environment suitable for anonymous Git network operations."""
    env = dict(os.environ)
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_PREFIX",
        "GIT_CEILING_DIRECTORIES",
        "AI_BASE_COMMIT",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_VALUE_0",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
        "GIT_ASKPASS",
        "SSH_ASKPASS",
        "SSH_AUTH_SOCK",
        "SSH_AGENT_PID",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "GH_ENTERPRISE_TOKEN",
    ):
        env.pop(key, None)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    return env


def anonymous_git_command(*args: str) -> list[str]:
    """Build a Git command that refuses to inherit credential helpers or auth headers."""
    return [
        "git",
        "-c",
        "credential.helper=",
        "-c",
        "http.extraHeader=",
        "-c",
        "core.askPass=",
        *args,
    ]


def highest_semver_tag(refs: str) -> str:
    tags = {
        match.group(1)
        for line in refs.splitlines()
        if (match := re.search(r"refs/tags/(v\d+\.\d+\.\d+)$", line))
    }
    if not tags:
        raise RuntimeError("public repository has no semantic-version tags")
    return max(tags, key=lambda tag: tuple(int(part) for part in tag[1:].split(".")))


def is_next_patch_release(candidate: str, published: str) -> bool:
    """Return whether *candidate* is exactly one patch after *published*."""
    pattern = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
    candidate_match = pattern.fullmatch(candidate)
    published_match = pattern.fullmatch(published)
    if not candidate_match or not published_match:
        return False
    candidate_parts = tuple(int(part) for part in candidate_match.groups())
    published_parts = tuple(int(part) for part in published_match.groups())
    return (
        candidate_parts[:2] == published_parts[:2] and candidate_parts[2] == published_parts[2] + 1
    )


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def supply_chain_issues(metadata: dict[str, object], *, root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    supply_chain = metadata.get("supplyChain")
    if not isinstance(supply_chain, dict):
        return ["release.json is missing supplyChain release evidence"]
    files = {key: root / path.relative_to(ROOT) for key, path in SUPPLY_CHAIN_FILES.items()}
    for key, path in files.items():
        expected = supply_chain.get(key)
        if not isinstance(expected, str) or not expected:
            issues.append(f"release.json supplyChain.{key} is missing")
            continue
        if not path.is_file():
            issues.append(
                f"release.json supplyChain.{key} source file is missing: {path.relative_to(root)}"
            )
            continue
        actual = file_digest(path)
        if actual != expected:
            issues.append(
                f"release.json supplyChain.{key} differs from {path.relative_to(root)} "
                f"(expected={expected}, actual={actual})"
            )
    if supply_chain.get("secretScanning") is not True:
        issues.append("release.json supplyChain.secretScanning must be true")
    return issues


def release_claims(metadata: dict[str, object]) -> dict[str, object]:
    """Return public release fields shared by the worktree and a published tag.

    Supply-chain digests are validated independently against each inspected tree.
    Excluding them here permits an unreleased worktree to regenerate evidence
    without claiming that the historical public tag already contains it.
    """
    return {key: metadata.get(key) for key in ("releaseTag", "publicContract", "capabilities")}


def release_asset_identity_issues(
    *,
    tag: str,
    tag_target: str,
    provenance: dict[str, object],
    release_digests: dict[str, object],
) -> list[str]:
    """Validate that release evidence names the exact immutable tag target."""
    issues: list[str] = []
    provenance_commit = provenance.get("commitSha")
    provenance_tag = provenance.get("releaseTag")
    digest_commit = release_digests.get("sourceCommit")
    digest_tag = release_digests.get("releaseTag")
    if not isinstance(provenance_commit, str) or not provenance_commit:
        issues.append("provenance commitSha is missing")
    elif provenance_commit != tag_target:
        issues.append(
            f"provenance commitSha {provenance_commit!r} differs from tag target {tag_target!r}"
        )
    if not isinstance(provenance_tag, str) or not provenance_tag:
        issues.append("provenance releaseTag is missing")
    elif provenance_tag != tag:
        issues.append(f"provenance releaseTag {provenance_tag!r} differs from tag {tag!r}")
    if not isinstance(digest_commit, str) or not digest_commit:
        issues.append("release digest sourceCommit is missing")
    elif digest_commit != tag_target:
        issues.append(
            f"release digest sourceCommit {digest_commit!r} differs from tag target {tag_target!r}"
        )
    if not isinstance(digest_tag, str) or not digest_tag:
        issues.append("release digest releaseTag is missing")
    elif digest_tag != tag:
        issues.append(f"release digest releaseTag {digest_tag!r} differs from tag {tag!r}")
    return issues


def public_release_asset_integrity_issues(
    *,
    tag: str,
    tag_target: str,
    tag_root: Path,
    assets: dict[str, bytes],
) -> list[str]:
    """Validate downloaded release evidence against the immutable tag tree.

    The release digest manifest is treated as a signed-by-content index only:
    every listed path is still rehashed from the cloned tag, and each public
    evidence asset is rehashed independently after download.
    """
    issues: list[str] = []
    required_public_assets = set(PUBLIC_ASSET_ARTIFACTS)
    missing_assets = required_public_assets - assets.keys()
    for name in sorted(missing_assets):
        issues.append(f"missing public asset: {name}")
    try:
        manifest = json.loads(assets["release-digests.json"].decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"release-digests.json is invalid: {exc}"]
    if not isinstance(manifest, dict):
        return ["release-digests.json must contain an object"]
    if manifest.get("format") != "ai-cockpit-release-digests" or manifest.get("version") != 1:
        issues.append("release-digests.json has an unsupported format or version")
    if manifest.get("sourceCommit") != tag_target:
        issues.append(
            f"release-digests.json sourceCommit {manifest.get('sourceCommit')!r} differs from tag target {tag_target!r}"
        )
    if manifest.get("releaseTag") != tag:
        issues.append(
            f"release-digests.json releaseTag {manifest.get('releaseTag')!r} differs from tag {tag!r}"
        )
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return issues + ["release-digests.json artifacts must contain an object"]
    missing_manifest = REQUIRED_MANIFEST_ARTIFACTS - set(artifacts)
    for relative in sorted(missing_manifest):
        issues.append(f"release-digests.json is missing artifact entry: {relative}")

    root = tag_root.resolve()
    for relative, expected in artifacts.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            issues.append("release-digests.json contains a non-string artifact entry")
            continue
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            issues.append(f"unsafe artifact path in release-digests.json: {relative}")
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            issues.append(f"invalid SHA-256 for manifest artifact: {relative}")
            continue
        if not candidate.is_file():
            issues.append(f"missing artifact in tag tree: {relative}")
            continue
        actual = file_digest(candidate)
        if actual != expected:
            issues.append(
                f"tag tree artifact digest mismatch for {relative} (expected={expected}, actual={actual})"
            )

    for asset_name, relative in PUBLIC_ASSET_ARTIFACTS.items():
        payload = assets.get(asset_name)
        if payload is None:
            continue
        expected = artifacts.get(relative)
        actual = hashlib.sha256(payload).hexdigest()
        if asset_name == "release-digests.json":
            expected = (
                actual
                if (root / relative).is_file() and payload == (root / relative).read_bytes()
                else None
            )
        if not isinstance(expected, str) or actual != expected:
            issues.append(
                f"public asset digest mismatch for {asset_name} (expected={expected!r}, actual={actual})"
            )
        tree_path = root / relative
        if tree_path.is_file() and payload != tree_path.read_bytes():
            issues.append(f"public asset bytes differ from tag tree: {asset_name}")
    manifest_path = root / ".ai" / "cockpit" / "release-digests.json"
    if manifest_path.is_file() and assets.get("release-digests.json") != manifest_path.read_bytes():
        issues.append("public release-digests.json bytes differ from tag tree")
    return issues


def fetch_published_release_assets(tag: str) -> dict[str, bytes]:
    """Download the public release evidence assets for *tag*."""
    parsed = urllib.parse.urlsplit(PUBLIC_REPOSITORY)
    repository_path = parsed.path.rstrip("/")
    if repository_path.endswith(".git"):
        repository_path = repository_path[:-4]
    api_url = f"{parsed.scheme}://{parsed.netloc}/api/v3/repos{repository_path}/releases/tags/{tag}"
    if parsed.netloc == "github.com":
        api_url = f"https://api.github.com/repos{repository_path}/releases/tags/{tag}"
    request = urllib.request.Request(
        api_url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "ai-cockpit-release-check"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        release = json.loads(response.read().decode("utf-8"))
    if not isinstance(release, dict) or release.get("draft") is True:
        raise RuntimeError(f"{tag}: published release is missing or still draft")
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise RuntimeError(f"{tag}: published release assets are missing")
    payloads: dict[str, bytes] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        url = asset.get("browser_download_url")
        if name in {"provenance.json", "release-digests.json", "sbom.json"} and isinstance(
            url, str
        ):
            asset_request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/octet-stream",
                    "User-Agent": "ai-cockpit-release-check",
                },
            )
            with urllib.request.urlopen(asset_request, timeout=30) as response:  # nosec B310
                payloads[name] = response.read()
    missing = {"provenance.json", "release-digests.json", "sbom.json"} - payloads.keys()
    if missing:
        raise RuntimeError(
            f"{tag}: published release is missing assets: {', '.join(sorted(missing))}"
        )
    return payloads


def fixture_archive(path: Path) -> None:
    payload = b"import sys\nprint('release contract fixture')\nsys.exit(0)\n"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("ai-cockpit/scripts/install_ai_cockpit.py")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))


def fake_git(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import os, shutil, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "i = 0\n"
        "while i < len(args) and args[i].startswith('-'):\n"
        "    if args[i] == '-C':\n"
        "        i += 2\n"
        "    else:\n"
        "        i += 1\n"
        "cmd = args[i] if i < len(args) else ''\n"
        "rest = args[i + 1:]\n"
        "if cmd == 'clone':\n"
        "    url = next(item for item in rest if item.startswith('https://') or item.startswith('git@'))\n"
        "    open(os.environ['URL_LOG'], 'w', encoding='utf-8').write(url)\n"
        "    destination = Path(rest[-1])\n"
        "    source = Path(os.environ['FAKE_SOURCE_DIR'])\n"
        "    if destination.exists():\n"
        "        shutil.rmtree(destination)\n"
        "    shutil.copytree(source, destination)\n"
        "elif cmd == 'archive':\n"
        "    out = rest[rest.index('-o') + 1]\n"
        "    archive = os.environ.get('RELEASE_CONTRACT_ARCHIVE') or os.environ['FAKE_ARCHIVE']\n"
        "    shutil.copy2(archive, out)\n"
        "else:\n"
        "    print(f'unexpected git invocation: {args!r}', file=sys.stderr)\n"
        "    sys.exit(1)\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def exercise_installer(script: bytes, *, tag: str, sha256_supported: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="ai-cockpit-release-") as raw:
        temp = Path(raw)
        target = temp / "target"
        bin_dir = temp / "bin"
        source_dir = temp / "source"
        target.mkdir()
        bin_dir.mkdir()
        (source_dir / "scripts").mkdir(parents=True)
        installer = temp / "install.sh"
        installer.write_bytes(script)
        installer.chmod(0o755)
        (source_dir / "scripts" / "install_ai_cockpit.py").write_text(
            "#!/usr/bin/env python3\nimport sys\nprint('release contract fixture')\nsys.exit(0)\n",
            encoding="utf-8",
        )
        archive = temp / "source.tar.gz"
        fixture_archive(archive)
        fake_git(bin_dir / "git")
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
                "AI_COCKPIT_TEMPLATE_REF": tag,
                "AI_COCKPIT_TEMPLATE_SHA256": "0" * 64,
                "FAKE_SOURCE_DIR": str(source_dir),
                "RELEASE_CONTRACT_ARCHIVE": str(archive),
                "URL_LOG": str(temp / "url.txt"),
            }
        )
        env.pop("AI_COCKPIT_TEMPLATE_SOURCE", None)
        result = subprocess.run(
            [str(installer), "--stack", "generic"],
            cwd=target,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    rejected_digest = result.returncode != 0 and "SHA256 mismatch" in result.stderr
    if rejected_digest != sha256_supported:
        raise RuntimeError(
            f"{tag}: SHA256 behavior disagrees with release.json "
            f"(declared={sha256_supported}, exit={result.returncode})"
        )


def run_command(
    command: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    if env is None:
        env = dict(os.environ)
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def exercise_public_distribution(
    script: bytes,
    *,
    tag: str,
    quality_target: str,
    source_path: str | None = None,
) -> None:
    """Install the real tagged distribution and exercise its documented adoption contract."""
    if not re.fullmatch(r"[A-Za-z0-9_.][A-Za-z0-9_.-]*", quality_target):
        raise RuntimeError(f"{tag}: invalid public quality target: {quality_target!r}")
    with tempfile.TemporaryDirectory(prefix="ai-cockpit-public-release-") as raw:
        project = Path(raw) / "project"
        project.mkdir()
        init_env = clean_git_environment()
        init_env["GIT_CEILING_DIRECTORIES"] = str(project.parent.resolve())
        init_result = run_command(["git", "init", "-q"], cwd=project, env=init_env)
        if init_result.returncode != 0:
            raise RuntimeError(
                f"{tag}: failed to initialize git repository: {init_result.stderr.strip()}"
            )
        isolated_env = init_env
        (project / "README.md").write_text("# Release contract fixture\n", encoding="utf-8")
        run_command(["git", "add", "README.md"], cwd=project, env=isolated_env)
        initial = run_command(
            [
                "git",
                "-c",
                "user.name=AI Cockpit",
                "-c",
                "user.email=release@example.invalid",
                "commit",
                "-qm",
                "initial",
            ],
            cwd=project,
            env=isolated_env,
        )
        if initial.returncode != 0:
            raise RuntimeError(
                f"{tag}: failed to create installation fixture: {initial.stderr.strip()}"
            )
        base = run_command(
            ["git", "rev-parse", "HEAD"], cwd=project, env=isolated_env
        ).stdout.strip()
        if (
            run_command(
                ["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=project, env=isolated_env
            ).returncode
            != 0
        ):
            raise RuntimeError(f"{tag}: fixture initial commit is not available: {base}")
        installer = project.parent / "install.sh"
        installer.write_bytes(script)
        installer.chmod(0o755)
        install_env = {**isolated_env}
        install_env.pop("AI_COCKPIT_TEMPLATE_SHA256", None)
        install_env["AI_COCKPIT_TEMPLATE_REF"] = tag
        if source_path:
            install_env["AI_COCKPIT_TEMPLATE_SOURCE"] = source_path
        installed = run_command(
            [str(installer), "--stack", "generic", "--update-makefile", "--create-adoption"],
            cwd=project,
            env=install_env,
        )
        if installed.returncode != 0:
            raise RuntimeError(
                f"{tag}: public installation failed:\n"
                f"--- STDOUT ---\n{installed.stdout}\n"
                f"--- STDERR ---\n{installed.stderr}"
            )
        if (
            run_command(
                ["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=project, env=isolated_env
            ).returncode
            != 0
        ):
            raise RuntimeError(
                f"{tag}: fixture initial commit disappeared after installation: {base}"
            )
        adoption_contract = (
            project / ".ai" / "work-items" / "active" / "adopt_ai_cockpit.contract.json"
        )
        try:
            recorded_base = json.loads(adoption_contract.read_text(encoding="utf-8"))["baseCommit"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"{tag}: cannot read adoption baseCommit: {exc}") from exc
        if recorded_base != base:
            raise RuntimeError(
                f"{tag}: adoption baseCommit escaped fixture repository "
                f"(expected={base}, recorded={recorded_base})"
            )
        target = run_command(["make", "-n", quality_target], cwd=project, env=isolated_env)
        if target.returncode != 0:
            raise RuntimeError(f"{tag}: documented Make target is missing: {quality_target}")
        quality = run_command(["make", quality_target], cwd=project, env=isolated_env)
        if quality.returncode == 0:
            output = " ".join((quality.stdout + quality.stderr).split())[:400]
            raise RuntimeError(
                f"{tag}: generic {quality_target} must fail closed before project configuration "
                f"(exit={quality.returncode}, output={output!r})"
            )
        readiness = run_command(["make", "check-ai-adoption-ready"], cwd=project, env=isolated_env)
        if readiness.returncode == 0:
            raise RuntimeError(f"{tag}: adoption readiness must fail before project calibration")
        finished = run_command(
            ["make", "ai-finish", "TASK=adopt_ai_cockpit"], cwd=project, env=isolated_env
        )
        if finished.returncode != 0:
            raise RuntimeError(
                f"{tag}: adoption finish failed:\n"
                f"--- STDOUT ---\n{finished.stdout}\n"
                f"--- STDERR ---\n{finished.stderr}"
            )
        run_command(["git", "add", "."], cwd=project, env=isolated_env)
        committed = run_command(
            [
                "git",
                "-c",
                "user.name=AI Cockpit",
                "-c",
                "user.email=release@example.invalid",
                "commit",
                "-qm",
                "adopt",
            ],
            cwd=project,
            env=isolated_env,
        )
        if committed.returncode != 0:
            raise RuntimeError(
                f"{tag}: failed to commit adoption:\n"
                f"--- STDOUT ---\n{committed.stdout}\n"
                f"--- STDERR ---\n{committed.stderr}"
            )
        audited = run_command(
            ["make", "check-ai-pr", f"AI_BASE_COMMIT={base}"], cwd=project, env=isolated_env
        )
        if audited.returncode != 0:
            raise RuntimeError(
                f"{tag}: adoption PR audit failed:\n"
                f"--- STDOUT ---\n{audited.stdout}\n"
                f"--- STDERR ---\n{audited.stderr}"
            )
        configured = run_command(
            [
                "make",
                "ai-start",
                "TASK=configure_ai_cockpit",
                "TITLE=Configure AI Cockpit for this project",
                "MODE=code",
            ],
            cwd=project,
            env=isolated_env,
        )
        if configured.returncode != 0:
            raise RuntimeError(
                f"{tag}: configuration Work Item creation failed:\n"
                f"--- STDOUT ---\n{configured.stdout}\n"
                f"--- STDERR ---\n{configured.stderr}"
            )
        active = project / ".ai" / "work-items" / "active"
        if (
            not (active / "configure_ai_cockpit.contract.json").is_file()
            or not (active / "configure_ai_cockpit.summary.json").is_file()
        ):
            raise RuntimeError(f"{tag}: configuration Work Item pair is missing")


def inspect_tagged_release(tag: str) -> tuple[dict[str, object], bytes, list[str]]:
    """Read release metadata, evidence, and installer exclusively from *tag*."""
    with tempfile.TemporaryDirectory(prefix="ai-cockpit-public-release-clone-") as raw:
        clone_dir = Path(raw) / "repo"
        clone = run_command(
            [
                *anonymous_git_command(
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    tag,
                    "--single-branch",
                    PUBLIC_REPOSITORY,
                    str(clone_dir),
                )
            ],
            cwd=Path(raw),
            env=clone_git_environment(),
        )
        if clone.returncode != 0:
            raise RuntimeError(f"failed to clone public release tag {tag}: {clone.stderr.strip()}")
        release_path = clone_dir / "release.json"
        if not release_path.is_file():
            raise RuntimeError(f"{tag}: cloned release is missing release.json")
        try:
            metadata = json.loads(release_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"{tag}: invalid release.json: {exc}") from exc
        if not isinstance(metadata, dict):
            raise RuntimeError(f"{tag}: release.json must contain an object")
        if metadata.get("releaseTag") != tag:
            raise RuntimeError(f"{tag}: tag release.json declares {metadata.get('releaseTag')!r}")
        installer = clone_dir / "install.sh"
        if not installer.is_file():
            raise RuntimeError(f"{tag}: cloned release is missing install.sh")
        issues = supply_chain_issues(metadata, root=clone_dir)
        if metadata.get("releaseEvidenceAuthority") == "release-assets-v1":
            tag_target = run_command(
                ["git", "rev-parse", "HEAD"], cwd=clone_dir, env=clone_git_environment()
            ).stdout.strip()
            try:
                assets = fetch_published_release_assets(tag)
                provenance = json.loads(assets["provenance.json"].decode("utf-8"))
                release_digests = json.loads(assets["release-digests.json"].decode("utf-8"))
            except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                issues.append(f"published release asset inspection failed: {exc}")
            else:
                issues.extend(
                    release_asset_identity_issues(
                        tag=tag,
                        tag_target=tag_target,
                        provenance=provenance,
                        release_digests=release_digests,
                    )
                )
                issues.extend(
                    public_release_asset_integrity_issues(
                        tag=tag,
                        tag_target=tag_target,
                        tag_root=clone_dir,
                        assets=assets,
                    )
                )
        return metadata, installer.read_bytes(), issues


def fetch_tagged_installer(tag: str) -> bytes:
    """Fetch the installer from an immutable public release tag."""
    with tempfile.TemporaryDirectory(prefix="ai-cockpit-public-release-installer-") as raw:
        clone_dir = Path(raw) / "repo"
        clone = run_command(
            [
                *anonymous_git_command(
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    tag,
                    "--single-branch",
                    PUBLIC_REPOSITORY,
                    str(clone_dir),
                )
            ],
            cwd=Path(raw),
            env=clone_git_environment(),
        )
        if clone.returncode != 0:
            raise RuntimeError(f"failed to clone public release tag {tag}: {clone.stderr.strip()}")
        installer = clone_dir / "install.sh"
        if not installer.is_file():
            raise RuntimeError(f"{tag}: cloned release is missing install.sh")
        return installer.read_bytes()


def list_remote_tags(repository_url: str) -> str:
    with tempfile.TemporaryDirectory(prefix="ai-cockpit-public-release-query-") as raw:
        query = run_command(
            [*anonymous_git_command("ls-remote", "--tags", "--refs", repository_url)],
            cwd=Path(raw),
            env=clone_git_environment(),
        )
        if query.returncode != 0:
            raise RuntimeError(f"failed to list public tags: {query.stderr.strip()}")
        return query.stdout


def main() -> int:
    metadata = json.loads(RELEASE.read_text(encoding="utf-8"))
    tag = metadata["releaseTag"]
    supported = metadata["capabilities"]["sha256ArchiveVerification"]
    quality_target = metadata["publicContract"]["projectQualityTarget"]
    local_source = os.environ.get("AI_COCKPIT_TEMPLATE_SOURCE")
    preparation_mode = os.environ.get("AI_RELEASE_PREPARATION") == "1"
    try:
        latest_tag = highest_semver_tag(list_remote_tags(PUBLIC_REPOSITORY))
        if tag != latest_tag:
            if preparation_mode and is_next_patch_release(tag, latest_tag):
                if supply_chain_issues(metadata):
                    raise RuntimeError("release-preparation evidence does not match local metadata")
                exercise_installer(
                    (ROOT / "install.sh").read_bytes(),
                    tag=tag,
                    sha256_supported=supported,
                )
                print(
                    f"release distribution check pending publication: {tag} follows public {latest_tag}"
                )
                return 0
            raise RuntimeError(
                f"release.json points to {tag}, but highest public tag is {latest_tag}"
            )
        tag_metadata, script, issues = inspect_tagged_release(tag)
        if release_claims(tag_metadata) != release_claims(metadata):
            raise RuntimeError(
                f"{tag}: release.json claims differ between the worktree and the inspected tag"
            )
        if issues:
            raise RuntimeError(f"{tag}: tag release evidence is invalid: {'; '.join(issues)}")
        exercise_installer(script, tag=tag, sha256_supported=supported)
        exercise_public_distribution(
            script, tag=tag, quality_target=quality_target, source_path=local_source
        )
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        print(f"release distribution check failed: {exc}", file=sys.stderr)
        return 1
    print(f"release distribution check passed: {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
