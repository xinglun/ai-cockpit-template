import json
import subprocess
import sys
from pathlib import Path

import pytest
import ai_calibrate

from ai_calibrate import (
    CALIBRATION_STAGES,
    CalibrationError,
    CalibrationSession,
    load_session,
)


def complete(session: CalibrationSession) -> None:
    for stage in CALIBRATION_STAGES:
        session.answer(stage, "Y", answer_type="yes_no")


def test_session_has_ten_japanese_stages_and_requires_na_reason():
    with pytest.raises(CalibrationError, match="session_id"):
        CalibrationSession.start("")
    session = CalibrationSession.start("test-session")
    assert session.data["language"] == "ja"
    assert [stage["id"] for stage in session.data["stages"]] == list(CALIBRATION_STAGES)
    assert set(session.data["stages"][0]["checklist"]["answerTypes"]) == {
        "yes_no",
        "alternative_input",
        "unknown",
        "not_applicable",
    }
    with pytest.raises(CalibrationError, match="requires a reason"):
        session.answer(CALIBRATION_STAGES[0], "N/A", answer_type="not_applicable")
    with pytest.raises(CalibrationError, match="already at the first"):
        session.back()
    with pytest.raises(CalibrationError, match="unsupported answer type"):
        session.answer(CALIBRATION_STAGES[0], "x", answer_type="invalid")
    with pytest.raises(CalibrationError, match="non-empty"):
        session.answer(CALIBRATION_STAGES[0], "", answer_type="alternative_input")
    with pytest.raises(CalibrationError, match="Y or N"):
        session.answer(CALIBRATION_STAGES[0], "maybe", answer_type="yes_no")


def test_pause_resume_back_review_and_stale_dependency_preserve_evidence():
    session = CalibrationSession.start("test-session")
    session.answer(CALIBRATION_STAGES[0], "Y", answer_type="yes_no")
    session.answer(CALIBRATION_STAGES[1], "Python", answer_type="alternative_input")
    session.answer(CALIBRATION_STAGES[2], "src", answer_type="alternative_input")
    session.pause()
    with pytest.raises(CalibrationError, match="resume"):
        session.answer(CALIBRATION_STAGES[2], "src", answer_type="alternative_input")
    session.resume()
    session.back()
    session.answer(CALIBRATION_STAGES[1], "TypeScript", answer_type="alternative_input")
    assert CALIBRATION_STAGES[2] in session.data["staleStages"]
    assert any(event["kind"] == "back" for event in session.data["events"])
    assert session.review()["status"] == "blocked"


def test_checks_confirmations_and_atomic_activation(tmp_path: Path):
    active = tmp_path / "active.json"
    active.write_text('{"old": true}\n', encoding="utf-8")
    session = CalibrationSession.start("test-session")
    complete(session)
    assert session.review()["status"] == "ready"
    assert session.stage_self_check()["status"] == "passed"
    assert session.full_self_check()["status"] == "passed"
    assert session.governance_simulation()["status"] == "passed"
    session.confirm("reviewer")
    session.confirm("owner")
    session.activate(active_path=active)
    assert json.loads(active.read_text(encoding="utf-8"))["sessionId"] == "test-session"

    failed = CalibrationSession.start("failed-session")
    complete(failed)
    failed.full_self_check()
    failed.governance_simulation()
    failed.confirm("reviewer")
    failed.confirm("owner")
    with pytest.raises(CalibrationError, match="failed closed"):
        failed.activate(active_path=active, fail=True)
    assert json.loads(active.read_text(encoding="utf-8"))["sessionId"] == "test-session"


def test_checks_fail_closed_before_completion_and_loader_rejects_bad_schema(tmp_path: Path):
    session = CalibrationSession.start("incomplete")
    assert session.stage_self_check()["status"] == "blocked"
    assert session.full_self_check()["status"] == "blocked"
    assert session.governance_simulation()["status"] == "blocked"
    with pytest.raises(CalibrationError, match="full self-check"):
        session.confirm("reviewer")
    with pytest.raises(CalibrationError, match="confirmation phase"):
        session.confirm("invalid")
    with pytest.raises(CalibrationError, match="both human"):
        session.activate(active_path=tmp_path / "active.json")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schemaVersion": 99, "language": "en"}), encoding="utf-8")
    with pytest.raises(CalibrationError, match="unsupported"):
        load_session(bad)


def test_session_persists_and_cli_runs_adopter_flow(tmp_path: Path):
    session_path = tmp_path / "session.json"
    active_path = tmp_path / "active.json"
    command = [sys.executable, "scripts/ai_calibrate.py", "session"]
    root = Path(__file__).resolve().parents[1]

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*command, *args, "--session", str(session_path)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    assert run("start", "--session-id", "fixture-session").returncode == 0
    assert run("answer").returncode == 1
    assert run("confirm").returncode == 1
    assert run("not-an-action").returncode != 0
    for stage in CALIBRATION_STAGES:
        assert (
            run("answer", "--stage", stage, "--answer", "Y", "--answer-type", "yes_no").returncode
            == 0
        )
    assert run("review").returncode == 0
    assert run("full-self-check").returncode == 0
    assert run("simulate").returncode == 0
    assert run("confirm", "--phase", "reviewer").returncode == 0
    assert run("confirm", "--phase", "owner").returncode == 0
    result = run("activate", "--active", str(active_path))
    assert result.returncode == 0, result.stderr
    assert load_session(session_path).data["state"] == "activated"
    assert json.loads(active_path.read_text(encoding="utf-8"))["sessionId"] == "fixture-session"


def test_cli_dispatch_is_exercised_in_process(tmp_path: Path, monkeypatch):
    session_path = tmp_path / "session.json"
    active_path = tmp_path / "active.json"

    def call(*args: str) -> int:
        monkeypatch.setattr(
            sys, "argv", ["ai_calibrate", "session", *args, "--session", str(session_path)]
        )
        return ai_calibrate.main()

    assert call("start", "--session-id", "in-process") == 0
    assert (
        call("answer", "--stage", CALIBRATION_STAGES[0], "--answer", "Y", "--answer-type", "yes_no")
        == 0
    )
    assert call("back") == 0
    for stage in CALIBRATION_STAGES:
        assert call("answer", "--stage", stage, "--answer", "Y", "--answer-type", "yes_no") == 0
    assert call("review") == 0
    assert call("pause") == 0
    assert call("resume") == 0
    assert call("stage-self-check") == 0
    assert call("full-self-check") == 0
    assert call("simulate") == 0
    assert call("confirm", "--phase", "reviewer") == 0
    assert call("confirm", "--phase", "owner") == 0
    assert call("activate", "--active", str(active_path)) == 0
