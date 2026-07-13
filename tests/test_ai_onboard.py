import subprocess
import sys
from pathlib import Path

import ai_onboard
import ai_common


ROOT = Path(__file__).resolve().parents[1]


def test_onboard_git_environment_helper_excludes_git_overrides():
    assert all(not key.startswith("GIT_") for key in ai_common.clean_git_environment())


def test_onboard_profile_status_detects_confirmed_and_proposed(tmp_path):
    (tmp_path / ".ai").mkdir()
    status, messages = ai_onboard.profile_status(tmp_path, "en")
    assert status == "missing"
    assert any("cockpit-calibrate" in message for message in messages)

    proposed = tmp_path / ".ai" / "project_profile.proposed.yaml"
    proposed.write_text("version: 1\n", encoding="utf-8")
    status, messages = ai_onboard.profile_status(tmp_path, "en")
    assert status == "proposed"
    assert any("project_profile.proposed.yaml" in message for message in messages)

    confirmed = tmp_path / ".ai" / "project_profile.yaml"
    confirmed.write_text("version: 1\n", encoding="utf-8")
    status, messages = ai_onboard.profile_status(tmp_path, "en")
    assert status == "confirmed"
    assert any("project_profile.yaml" in message for message in messages)


def test_onboard_readiness_actions_flags_placeholders_and_coverage(tmp_path):
    (tmp_path / ".ai" / "guards").mkdir(parents=True)
    (tmp_path / ".ai" / "guards" / "coverage_policy.yaml").write_text(
        "adoptionReviewed: false\n",
        encoding="utf-8",
    )
    (tmp_path / "Makefile.ai.stack").write_text(
        "PROJECT_TEST = printf 'ERROR: configure PROJECT_TEST' >&2; false\n",
        encoding="utf-8",
    )
    passed, actions = ai_onboard.readiness_actions(tmp_path, "en")
    assert any("Makefile.ai.stack" in action for action in actions)
    assert any("adoptionReviewed" in action for action in actions)
    assert any("CI" in action for action in actions)
    assert not passed or isinstance(passed, list)


def test_onboard_resolve_locale_prefers_explicit_and_lang(monkeypatch):
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    assert ai_onboard.resolve_locale("ja") == "ja"
    assert ai_onboard.resolve_locale("en") == "en"
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    assert ai_onboard.resolve_locale(None) == "ja"


def test_onboard_phase_one_runs_in_repository(capsys):
    code = ai_onboard.phase_environment(ROOT, "en")
    output = capsys.readouterr().out
    assert "Phase 1/3" in output
    assert "[PASS]" in output
    assert code == 0


def test_onboard_main_single_phase_three(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_onboard, "phase_readiness", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_onboard.py", "--root", str(tmp_path), "--phase", "3", "--skip-readiness-checks"],
    )
    assert ai_onboard.main() == 0


def test_onboard_cli_entrypoint(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "ai_onboard.py"),
            "--root",
            str(tmp_path),
            "--phase",
            "3",
            "--skip-readiness-checks",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Phase 3/3" in result.stdout


def test_onboard_run_all_short_circuits_on_environment_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_onboard, "phase_environment", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(ai_onboard, "phase_calibration", lambda *_args, **_kwargs: 0)
    assert ai_onboard.run_all(tmp_path, "en", run_calibrate=True, run_checks=False) == 1


def test_onboard_phase_calibration_runs_profile_checks(tmp_path, monkeypatch):
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai" / "project_profile.yaml").write_text("version: 1\n", encoding="utf-8")
    calls: list[str] = []

    def fake_make(_root: Path, target: str) -> tuple[int, str]:
        calls.append(target)
        return 0, f"{target} ok"

    monkeypatch.setattr(ai_onboard, "run_make", fake_make)
    assert ai_onboard.phase_calibration(tmp_path, "en", run_calibrate=False) == 0
    assert calls == ["check-ai-project-profile", "check-ai-guard-calibration"]
