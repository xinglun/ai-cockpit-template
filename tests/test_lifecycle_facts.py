from __future__ import annotations

import json
from pathlib import Path

from ai_lifecycle_facts import lifecycle_facts


def test_lifecycle_facts_reports_bootstrap_without_claiming_readiness(tmp_path: Path) -> None:
    facts = lifecycle_facts(tmp_path)
    assert facts["state"] == "bootstrap"
    assert facts["readiness"] == "not_claimed"
    assert facts["enterpriseAssurance"] == "not_claimed"
    assert "provider_assets" in facts["notRun"]


def test_lifecycle_facts_reports_calibration_and_active_work_item(tmp_path: Path) -> None:
    ai_dir = tmp_path / ".ai"
    active = ai_dir / "work-items" / "active"
    active.mkdir(parents=True)
    (ai_dir / "project_profile.proposed.yaml").write_text("profile: proposed\n", encoding="utf-8")
    (active / "demo.contract.json").write_text("{}\n", encoding="utf-8")
    (active / "demo.summary.json").write_text("{}\n", encoding="utf-8")
    facts = lifecycle_facts(tmp_path)
    assert facts["state"] == "calibration"
    assert facts["profile"]["proposed"] is True
    assert facts["activeWorkItems"]["contractCount"] == 1


def test_lifecycle_facts_reports_governed_and_no_active_states(tmp_path: Path) -> None:
    ai_dir = tmp_path / ".ai"
    ai_dir.mkdir()
    (ai_dir / "project_profile.yaml").write_text("profile: confirmed\n", encoding="utf-8")
    (ai_dir / "work-items" / "active").mkdir(parents=True)
    assert lifecycle_facts(tmp_path)["state"] == "no_active_work_item"
    active = ai_dir / "work-items" / "active"
    (active / "demo.contract.json").write_text("{}\n", encoding="utf-8")
    assert lifecycle_facts(tmp_path)["state"] == "governed_development"


def test_cli_output_is_deterministic_json(tmp_path: Path, capsys, monkeypatch) -> None:
    from ai_lifecycle_facts import main

    monkeypatch.setattr("sys.argv", ["ai_lifecycle_facts", "--root", str(tmp_path)])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["schemaVersion"] == 1
