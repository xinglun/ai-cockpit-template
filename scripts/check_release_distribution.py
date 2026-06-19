#!/usr/bin/env python3
"""Verify the documented release tag against its public installer behavior."""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release.json"
PUBLIC_REPOSITORY = "https://github.com/xinglun/ai-cockpit-template.git"


def highest_semver_tag(refs: str) -> str:
    tags = {
        match.group(1)
        for line in refs.splitlines()
        if (match := re.search(r"refs/tags/(v\d+\.\d+\.\d+)$", line))
    }
    if not tags:
        raise RuntimeError("public repository has no semantic-version tags")
    return max(tags, key=lambda tag: tuple(int(part) for part in tag[1:].split(".")))


def fixture_archive(path: Path) -> None:
    payload = b"import sys\nprint('release contract fixture')\nsys.exit(0)\n"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("ai-cockpit/scripts/install_ai_cockpit.py")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))


def fake_curl(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import os, shutil, sys\n"
        "args = sys.argv[1:]\n"
        "archive = os.environ['RELEASE_CONTRACT_ARCHIVE']\n"
        "if '-o' in args:\n"
        "    shutil.copy2(archive, args[args.index('-o') + 1])\n"
        "else:\n"
        "    sys.stdout.buffer.write(open(archive, 'rb').read())\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def exercise_installer(script: bytes, *, tag: str, sha256_supported: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="ai-cockpit-release-") as raw:
        temp = Path(raw)
        target = temp / "target"
        bin_dir = temp / "bin"
        target.mkdir()
        bin_dir.mkdir()
        installer = temp / "install.sh"
        installer.write_bytes(script)
        installer.chmod(0o755)
        archive = temp / "source.tar.gz"
        fixture_archive(archive)
        fake_curl(bin_dir / "curl")
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
                "AI_COCKPIT_TEMPLATE_REF": tag,
                "AI_COCKPIT_TEMPLATE_SHA256": "0" * 64,
                "RELEASE_CONTRACT_ARCHIVE": str(archive),
            }
        )
        result = subprocess.run(
            [str(installer), "--stack", "generic"], cwd=target, env=env,
            text=True, capture_output=True, check=False,
        )
    rejected_digest = result.returncode != 0 and "SHA256 mismatch" in result.stderr
    if rejected_digest != sha256_supported:
        raise RuntimeError(
            f"{tag}: SHA256 behavior disagrees with release.json "
            f"(declared={sha256_supported}, exit={result.returncode})"
        )


def run_command(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def exercise_public_distribution(script: bytes, *, tag: str, quality_target: str) -> None:
    """Install the real tagged distribution and exercise its documented adoption contract."""
    if not re.fullmatch(r"[A-Za-z0-9_.][A-Za-z0-9_.-]*", quality_target):
        raise RuntimeError(f"{tag}: invalid public quality target: {quality_target!r}")
    with tempfile.TemporaryDirectory(prefix="ai-cockpit-public-release-") as raw:
        project = Path(raw) / "project"
        project.mkdir()
        run_command(["git", "init", "-q"], cwd=project)
        (project / "README.md").write_text("# Release contract fixture\n", encoding="utf-8")
        run_command(["git", "add", "README.md"], cwd=project)
        initial = run_command(
            ["git", "-c", "user.name=AI Cockpit", "-c", "user.email=release@example.invalid", "commit", "-qm", "initial"],
            cwd=project,
        )
        if initial.returncode != 0:
            raise RuntimeError(f"{tag}: failed to create installation fixture: {initial.stderr.strip()}")
        base = run_command(["git", "rev-parse", "HEAD"], cwd=project).stdout.strip()
        installer = project.parent / "install.sh"
        installer.write_bytes(script)
        installer.chmod(0o755)
        env = os.environ.copy()
        env.pop("AI_COCKPIT_TEMPLATE_SHA256", None)
        env["AI_COCKPIT_TEMPLATE_REF"] = tag
        installed = run_command(
            [str(installer), "--stack", "generic", "--update-makefile", "--create-adoption"],
            cwd=project,
            env=env,
        )
        if installed.returncode != 0:
            raise RuntimeError(f"{tag}: public installation failed: {installed.stderr.strip()}")
        target = run_command(["make", "-n", quality_target], cwd=project)
        if target.returncode != 0:
            raise RuntimeError(f"{tag}: documented Make target is missing: {quality_target}")
        quality = run_command(["make", quality_target], cwd=project)
        if quality.returncode == 0:
            output = " ".join((quality.stdout + quality.stderr).split())[:400]
            raise RuntimeError(
                f"{tag}: generic {quality_target} must fail closed before project configuration "
                f"(exit={quality.returncode}, output={output!r})"
            )
        readiness = run_command(["make", "check-ai-adoption-ready"], cwd=project)
        if readiness.returncode == 0:
            raise RuntimeError(f"{tag}: adoption readiness must fail before project calibration")
        finished = run_command(["make", "ai-finish", "TASK=adopt_ai_cockpit"], cwd=project)
        if finished.returncode != 0:
            raise RuntimeError(f"{tag}: adoption finish failed: {finished.stderr.strip()}")
        run_command(["git", "add", "."], cwd=project)
        committed = run_command(
            ["git", "-c", "user.name=AI Cockpit", "-c", "user.email=release@example.invalid", "commit", "-qm", "adopt"],
            cwd=project,
        )
        if committed.returncode != 0:
            raise RuntimeError(f"{tag}: failed to commit adoption: {committed.stderr.strip()}")
        audited = run_command(["make", "check-ai-pr", f"AI_BASE_COMMIT={base}"], cwd=project)
        if audited.returncode != 0:
            raise RuntimeError(f"{tag}: adoption PR audit failed: {audited.stderr.strip()}")
        configured = run_command(
            [
                "make", "ai-start", "TASK=configure_ai_cockpit",
                "TITLE=Configure AI Cockpit for this project", "MODE=code",
            ],
            cwd=project,
        )
        if configured.returncode != 0:
            raise RuntimeError(f"{tag}: configuration Work Item creation failed: {configured.stderr.strip()}")
        active = project / ".ai" / "work-items" / "active"
        if not (active / "configure_ai_cockpit.contract.json").is_file() or not (
            active / "configure_ai_cockpit.summary.json"
        ).is_file():
            raise RuntimeError(f"{tag}: configuration Work Item pair is missing")


def main() -> int:
    metadata = json.loads(RELEASE.read_text(encoding="utf-8"))
    tag = metadata["releaseTag"]
    supported = metadata["capabilities"]["sha256ArchiveVerification"]
    quality_target = metadata["publicContract"]["projectQualityTarget"]
    url = f"https://raw.githubusercontent.com/xinglun/ai-cockpit-template/{tag}/install.sh"
    try:
        tags = run_command(["git", "ls-remote", "--tags", "--refs", PUBLIC_REPOSITORY], cwd=ROOT)
        if tags.returncode != 0:
            raise RuntimeError(f"failed to list public tags: {tags.stderr.strip()}")
        latest_tag = highest_semver_tag(tags.stdout)
        if tag != latest_tag:
            raise RuntimeError(f"release.json points to {tag}, but highest public tag is {latest_tag}")
        # The URL is constructed from a fixed HTTPS GitHub origin and a validated release tag.
        with urllib.request.urlopen(url, timeout=30) as response:  # nosec B310
            script = response.read()
        exercise_installer(script, tag=tag, sha256_supported=supported)
        exercise_public_distribution(script, tag=tag, quality_target=quality_target)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f"release distribution check failed: {exc}", file=sys.stderr)
        return 1
    print(f"release distribution check passed: {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
