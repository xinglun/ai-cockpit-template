import subprocess
import sys
from pathlib import Path

import ai_doctor


ROOT = Path(__file__).resolve().parents[1]


def test_doctor_passes_hard_prerequisites_for_repository():
    passed, warnings, failures = ai_doctor.diagnose(ROOT)
    assert not failures
    assert passed
    assert any("Coverage Guard" in warning for warning in warnings)
    assert any("check-ai-adoption-ready" in warning for warning in warnings)


def test_doctor_fails_without_git_repository_or_initial_commit(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ai_doctor.py"), "--root", str(tmp_path)],
        text=True, capture_output=True, check=False,
    )

    assert result.returncode == 1
    assert "[FAIL] Run inside a Git repository" in result.stdout
    assert "[FAIL] Create an initial Git commit" in result.stdout


def test_doctor_warns_for_unconfigured_project_quality(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    (tmp_path / "Makefile.ai.stack").write_text(
        "PROJECT_TEST = printf 'ERROR: configure PROJECT_TEST' >&2; false\n", encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)

    _, warnings, failures = ai_doctor.diagnose(tmp_path)
    assert not failures
    assert any("placeholders" in warning for warning in warnings)
