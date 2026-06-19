#!/usr/bin/env python3
"""Verify the documented release tag against its public installer behavior."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release.json"


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


def main() -> int:
    metadata = json.loads(RELEASE.read_text(encoding="utf-8"))
    tag = metadata["releaseTag"]
    supported = metadata["capabilities"]["sha256ArchiveVerification"]
    url = f"https://raw.githubusercontent.com/xinglun/ai-cockpit-template/{tag}/install.sh"
    try:
        # The URL is constructed from a fixed HTTPS GitHub origin and a validated release tag.
        with urllib.request.urlopen(url, timeout=30) as response:  # nosec B310
            script = response.read()
        exercise_installer(script, tag=tag, sha256_supported=supported)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f"release distribution check failed: {exc}", file=sys.stderr)
        return 1
    print(f"release distribution check passed: {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
