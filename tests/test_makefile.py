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


def test_make_prefers_project_venv_and_allows_explicit_python_override():
    automatic = subprocess.run(
        ["make", "-n", "test"], cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert automatic.returncode == 0
    assert ".venv/bin/python -m pytest" in automatic.stdout

    explicit = subprocess.run(
        ["make", "-n", "test", "PYTHON=/custom/python"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert explicit.returncode == 0
    assert "/custom/python -m pytest" in explicit.stdout
