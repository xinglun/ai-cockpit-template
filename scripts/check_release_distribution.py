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
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release.json"
PUBLIC_REPOSITORY = os.environ.get(
    "AI_COCKPIT_TEMPLATE_PUBLIC_REPOSITORY",
    "https://github.com/xinglun/ai-cockpit-template.git",
)


def clean_git_environment() -> dict[str, str]:
    """Return an environment with no ambient Git repository or baseline overrides."""
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key != "AI_BASE_COMMIT"
    }


def clone_git_environment() -> dict[str, str]:
    """Return an environment suitable for cloning without ambient repo state."""
    env = dict(os.environ)
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_PREFIX",
        "GIT_CEILING_DIRECTORIES",
        "AI_BASE_COMMIT",
    ):
        env.pop(key, None)
    return env


def highest_semver_tag(refs: str) -> str:
    tags = {
        match.group(1)
        for line in refs.splitlines()
        if (match := re.search(r"refs/tags/(v\d+\.\d+\.\d+)$", line))
    }
    if not tags:
        raise RuntimeError("public repository has no semantic-version tags")
    return max(tags, key=lambda tag: tuple(int(part) for part in tag[1:].split(".")))


def git_extraheader_args(repository_url: str) -> list[str]:
    """Return `git -c` overrides for any checkout-auth header on the current repo."""
    host = urlsplit(repository_url).netloc
    if not host:
        return []
    config_key = f"http.https://{host}/.extraheader"
    result = run_command(
        ["git", "config", "--local", "--get-all", config_key],
        cwd=ROOT,
        env=clean_git_environment(),
    )
    if result.returncode != 0:
        return []
    args: list[str] = []
    for header in result.stdout.splitlines():
        header = header.strip()
        if header:
            args.extend(["-c", f"{config_key}={header}"])
    return args


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
            raise RuntimeError(f"{tag}: failed to initialize git repository: {init_result.stderr.strip()}")
        isolated_env = init_env
        (project / "README.md").write_text("# Release contract fixture\n", encoding="utf-8")
        run_command(["git", "add", "README.md"], cwd=project, env=isolated_env)
        initial = run_command(
            ["git", "-c", "user.name=AI Cockpit", "-c", "user.email=release@example.invalid", "commit", "-qm", "initial"],
            cwd=project,
            env=isolated_env,
        )
        if initial.returncode != 0:
            raise RuntimeError(f"{tag}: failed to create installation fixture: {initial.stderr.strip()}")
        base = run_command(["git", "rev-parse", "HEAD"], cwd=project, env=isolated_env).stdout.strip()
        if run_command(["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=project, env=isolated_env).returncode != 0:
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
        if run_command(["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=project, env=isolated_env).returncode != 0:
            raise RuntimeError(f"{tag}: fixture initial commit disappeared after installation: {base}")
        adoption_contract = project / ".ai" / "work-items" / "active" / "adopt_ai_cockpit.contract.json"
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
        finished = run_command(["make", "ai-finish", "TASK=adopt_ai_cockpit"], cwd=project, env=isolated_env)
        if finished.returncode != 0:
            raise RuntimeError(
                f"{tag}: adoption finish failed:\n"
                f"--- STDOUT ---\n{finished.stdout}\n"
                f"--- STDERR ---\n{finished.stderr}"
            )
        run_command(["git", "add", "."], cwd=project, env=isolated_env)
        committed = run_command(
            ["git", "-c", "user.name=AI Cockpit", "-c", "user.email=release@example.invalid", "commit", "-qm", "adopt"],
            cwd=project,
            env=isolated_env,
        )
        if committed.returncode != 0:
            raise RuntimeError(
                f"{tag}: failed to commit adoption:\n"
                f"--- STDOUT ---\n{committed.stdout}\n"
                f"--- STDERR ---\n{committed.stderr}"
            )
        audited = run_command(["make", "check-ai-pr", f"AI_BASE_COMMIT={base}"], cwd=project, env=isolated_env)
        if audited.returncode != 0:
            raise RuntimeError(
                f"{tag}: adoption PR audit failed:\n"
                f"--- STDOUT ---\n{audited.stdout}\n"
                f"--- STDERR ---\n{audited.stderr}"
            )
        configured = run_command(
            [
                "make", "ai-start", "TASK=configure_ai_cockpit",
                "TITLE=Configure AI Cockpit for this project", "MODE=code",
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
        if not (active / "configure_ai_cockpit.contract.json").is_file() or not (
            active / "configure_ai_cockpit.summary.json"
        ).is_file():
            raise RuntimeError(f"{tag}: configuration Work Item pair is missing")


def fetch_tagged_installer(tag: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="ai-cockpit-public-release-clone-") as raw:
        clone_dir = Path(raw) / "repo"
        clone = run_command(
            [
                "git",
                *git_extraheader_args(PUBLIC_REPOSITORY),
                "clone",
                "--depth",
                "1",
                "--branch",
                tag,
                "--single-branch",
                PUBLIC_REPOSITORY,
                str(clone_dir),
            ],
            cwd=ROOT,
            env=clone_git_environment(),
        )
        if clone.returncode != 0:
            raise RuntimeError(f"failed to clone public release tag {tag}: {clone.stderr.strip()}")
        installer = clone_dir / "install.sh"
        if not installer.is_file():
            raise RuntimeError(f"{tag}: cloned release is missing install.sh")
        return installer.read_bytes()


def main() -> int:
    metadata = json.loads(RELEASE.read_text(encoding="utf-8"))
    tag = metadata["releaseTag"]
    supported = metadata["capabilities"]["sha256ArchiveVerification"]
    quality_target = metadata["publicContract"]["projectQualityTarget"]
    local_source = os.environ.get("AI_COCKPIT_TEMPLATE_SOURCE")
    try:
        tags = run_command(
            ["git", *git_extraheader_args(PUBLIC_REPOSITORY), "ls-remote", "--tags", "--refs", PUBLIC_REPOSITORY],
            cwd=ROOT,
        )
        if tags.returncode != 0:
            raise RuntimeError(f"failed to list public tags: {tags.stderr.strip()}")
        latest_tag = highest_semver_tag(tags.stdout)
        if tag != latest_tag:
            raise RuntimeError(f"release.json points to {tag}, but highest public tag is {latest_tag}")
        script = fetch_tagged_installer(tag)
        exercise_installer(script, tag=tag, sha256_supported=supported)
        exercise_public_distribution(script, tag=tag, quality_target=quality_target, source_path=local_source)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        print(f"release distribution check failed: {exc}", file=sys.stderr)
        return 1
    print(f"release distribution check passed: {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
