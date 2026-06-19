import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_check_ai_pr_uses_aggregate_validator():
    result = subprocess.run(
        ["make", "-n", "check-ai-pr", "AI_BASE_COMMIT=abc123"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'scripts/ai_check_pr.py --base "abc123"' in result.stdout


def test_project_governance_make_targets_are_public():
    result = subprocess.run(
        ["make", "-n", "cockpit-doctor", "cockpit-calibrate", "cockpit-validate-calibration", "check-ai-guard-calibration"],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ai_project_doctor.py" in result.stdout
    assert "ai_calibrate.py generate" in result.stdout
    assert "ai_check_guard_calibration.py" in result.stdout


def test_make_prefers_project_venv_and_allows_explicit_python_override(tmp_path):
    makefile_content = (ROOT / "Makefile").read_text(encoding="utf-8")
    (tmp_path / "Makefile").write_text(makefile_content, encoding="utf-8")

    # When no .venv exists, defaults to python3
    automatic_no_venv = subprocess.run(
        ["make", "-n", "test"], cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert automatic_no_venv.returncode == 0
    assert "python3 -m pytest" in automatic_no_venv.stdout

    # When .venv exists, uses .venv/bin/python
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.touch()

    automatic_with_venv = subprocess.run(
        ["make", "-n", "test"], cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert automatic_with_venv.returncode == 0
    assert ".venv/bin/python -m pytest" in automatic_with_venv.stdout

    # Explicit override works regardless
    explicit = subprocess.run(
        ["make", "-n", "test", "PYTHON=/custom/python"],
        cwd=tmp_path, text=True, capture_output=True, check=False,
    )
    assert explicit.returncode == 0
    assert "/custom/python -m pytest" in explicit.stdout
