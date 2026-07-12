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
    assert any("role=adopted or unconfirmed template" in warning for warning in warnings)


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


def test_doctor_reports_adoption_ready_when_configuration_complete(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    (tmp_path / "Makefile.ai.stack").write_text("PROJECT_TEST = true\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".ai" / "guards").mkdir(parents=True)
    (tmp_path / ".ai" / "guards" / "coverage_policy.yaml").write_text("adoptionReviewed: true\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    monkeypatch.setattr(ai_doctor, "readiness_failures", lambda _root: [])

    passed, warnings, failures = ai_doctor.diagnose(tmp_path)
    assert not failures
    assert any("Adoption readiness configuration is complete" in item for item in passed)
    assert any("Coverage Guard" in warning for warning in warnings)


def test_doctor_warns_when_worktree_is_dirty(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    (tmp_path / "dirty.txt").write_text("pending\n", encoding="utf-8")

    _, warnings, failures = ai_doctor.diagnose(tmp_path)
    assert not failures
    assert any("worktree is dirty" in warning for warning in warnings)


def test_doctor_warns_when_stack_file_is_missing(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)

    _, warnings, failures = ai_doctor.diagnose(tmp_path)
    assert not failures
    assert any("Makefile.ai.stack is missing" in warning for warning in warnings)


def test_doctor_command_ok_handles_os_error(monkeypatch):
    def raise_os_error(*_args, **_kwargs):
        raise OSError("missing")

    monkeypatch.setattr(ai_doctor.subprocess, "run", raise_os_error)
    assert ai_doctor.command_ok(Path("."), "git", "status") is False


def test_doctor_diagnose_handles_git_status_os_error(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)

    original_run = ai_doctor.subprocess.run

    def selective_run(command, **kwargs):
        if command[:2] == ["git", "status"]:
            raise OSError("git unavailable")
        return original_run(command, **kwargs)

    monkeypatch.setattr(ai_doctor.subprocess, "run", selective_run)
    passed, _, failures = ai_doctor.diagnose(tmp_path)
    assert not failures
    assert any("Git worktree is clean" in item for item in passed)


def test_doctor_main_prints_warnings_without_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        ai_doctor,
        "diagnose",
        lambda _root: (["ok"], ["needs review"], []),
    )
    monkeypatch.setattr(sys, "argv", ["ai_doctor.py", "--root", str(tmp_path)])
    assert ai_doctor.main() == 0
    output = capsys.readouterr().out
    assert "[WARN] needs review" in output
    assert "[PASS] ok" in output


def test_doctor_main_returns_nonzero_on_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ai_doctor, "diagnose", lambda _root: ([], [], ["Run inside a Git repository"]))
    monkeypatch.setattr(sys, "argv", ["ai_doctor.py", "--root", str(tmp_path)])
    assert ai_doctor.main() == 1
    assert "[FAIL]" in capsys.readouterr().out
