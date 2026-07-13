import os
import subprocess
import sys
from pathlib import Path

from install_ai_cockpit import Installer


ROOT = Path(__file__).resolve().parents[1]


def run(
    cwd: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False, env=env)


def bootstrap_python_project(tmp_path: Path) -> None:
    assert run(tmp_path, "git", "init", "-q").returncode == 0
    assert run(tmp_path, "git", "config", "user.email", "test@example.invalid").returncode == 0
    assert run(tmp_path, "git", "config", "user.name", "Test").returncode == 0
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tmp_path / "tests" / "test_app.py").write_text(
        "from src.app import add\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
        encoding="utf-8",
    )
    assert run(tmp_path, "git", "add", ".").returncode == 0
    assert run(tmp_path, "git", "commit", "-qm", "initial").returncode == 0


def test_onboard_full_journey_after_fresh_install(tmp_path):
    bootstrap_python_project(tmp_path)
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="python",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=False,
    )
    assert installer.install() == 0

    env = os.environ.copy()
    env["PYTHON"] = sys.executable
    onboard = run(
        tmp_path,
        "make",
        "ai-onboard",
        "SKIP_READINESS_CHECKS=1",
        f"PYTHON={sys.executable}",
        env=env,
    )
    assert onboard.returncode == 0, onboard.stdout + onboard.stderr
    assert "Phase 1/3" in onboard.stdout
    assert "Phase 2/3" in onboard.stdout
    assert "Phase 3/3" in onboard.stdout
    assert (tmp_path / ".ai" / "project_profile.proposed.yaml").is_file()


def test_onboard_japanese_output_via_locale_flag(tmp_path):
    result = run(
        tmp_path,
        sys.executable,
        str(ROOT / "scripts" / "ai_onboard.py"),
        "--root",
        str(tmp_path),
        "--phase",
        "1",
        "--locale",
        "ja",
    )
    assert "フェーズ 1/3" in result.stdout
    assert "環境確認" in result.stdout
