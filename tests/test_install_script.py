import hashlib
import io
import os
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def make_archive(path: Path) -> None:
    payload = b"import sys\nprint('stub installer')\nsys.exit(0)\n"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("ai-cockpit/scripts/install_ai_cockpit.py")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))


def make_fake_curl(bin_dir: Path) -> Path:
    curl = bin_dir / "curl"
    curl.write_text(
        "#!/usr/bin/env python3\n"
        "import os, shutil, sys\n"
        "args = sys.argv[1:]\n"
        "url = next(item for item in args if item.startswith('https://'))\n"
        "open(os.environ['URL_LOG'], 'w', encoding='utf-8').write(url)\n"
        "shutil.copy2(os.environ['FAKE_ARCHIVE'], args[args.index('-o') + 1])\n",
        encoding="utf-8",
    )
    curl.chmod(0o755)
    return curl


def run_remote_install(tmp_path: Path, expected_sha256: str) -> subprocess.CompletedProcess[str]:
    runner = tmp_path / "runner"
    target = tmp_path / "target"
    fake_bin = tmp_path / "bin"
    runner.mkdir()
    target.mkdir()
    fake_bin.mkdir()
    script = runner / "install.sh"
    script.write_bytes((ROOT / "install.sh").read_bytes())
    script.chmod(0o755)
    archive = tmp_path / "source.tar.gz"
    make_archive(archive)
    if expected_sha256 == "MATCH":
        expected_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
    make_fake_curl(fake_bin)
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
            "FAKE_ARCHIVE": str(archive),
            "URL_LOG": str(tmp_path / "url.txt"),
            "AI_COCKPIT_TEMPLATE_SHA256": expected_sha256,
        }
    )
    return subprocess.run(
        [str(script), "--stack", "generic"], cwd=target, env=env,
        text=True, capture_output=True, check=False,
    )


def test_remote_install_defaults_to_fixed_release_and_accepts_matching_sha256(tmp_path):
    result = run_remote_install(tmp_path, "MATCH")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "url.txt").read_text(encoding="utf-8").endswith("/archive/v0.5.9.tar.gz")
    assert "Verified archive SHA256:" in result.stdout


def test_remote_install_rejects_sha256_mismatch_before_extraction(tmp_path):
    result = run_remote_install(tmp_path, "0" * 64)

    assert result.returncode == 2
    assert "archive SHA256 mismatch" in result.stderr
    assert "stub installer" not in result.stdout
