from pathlib import Path

from ai_readiness_policy import readiness_state


def test_readiness_policy_does_not_call_installation_production_ready(tmp_path: Path):
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    (tmp_path / ".ai" / "cockpit" / "version.json").write_text("{}", encoding="utf-8")
    state = readiness_state(tmp_path)
    assert state["adoptionInstalled"] is True
    assert state["productionReady"] is False
