import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_calibration_inventory import (
    INVENTORY_KEYS,
    STATUS_VALUES,
    build_inventory,
    validate_inventory,
)
from ai_governance_compression import render_active_status


def test_inventory_has_one_explicit_entry_for_each_calibration_boundary(tmp_path: Path):
    inventory = build_inventory(tmp_path)

    assert tuple(inventory["items"]) == INVENTORY_KEYS
    assert set(inventory["summary"]) == set(STATUS_VALUES)
    for key, item in inventory["items"].items():
        assert item["key"] == key
        assert item["status"] in STATUS_VALUES
        assert item["source"]
        assert item["confirmation"] in {"none", "static", "command", "human", "external"}
        assert isinstance(item["evidence"], list)
        assert "staleAt" in item
        assert item["owner"]
        assert "blockingReason" in item
    assert validate_inventory(inventory) == []


def test_inventory_distinguishes_command_evidence_from_static_configuration(tmp_path: Path):
    (tmp_path / "Makefile.ai.stack").write_text(
        "PROJECT_FORMAT_CHECK = formatter --check\n"
        "PROJECT_TEST = pytest\n"
        "PROJECT_LINT = ruff check\n",
        encoding="utf-8",
    )
    evidence = {
        "quality": {
            "status": "complete",
            "source": "make ai-cockpit-quality",
            "confirmation": "command",
            "evidence": ["target/quality-run.json"],
        },
        "ci": {
            "status": "complete",
            "source": "workflow run 42",
            "confirmation": "external",
            "evidence": ["run=42", "headSha=abc123"],
        },
    }

    inventory = build_inventory(tmp_path, command_evidence=evidence)

    assert inventory["items"]["quality"]["status"] == "complete"
    assert inventory["items"]["quality"]["confirmation"] == "command"
    assert inventory["items"]["ci"]["status"] == "complete"
    assert inventory["items"]["ci"]["confirmation"] == "external"
    assert inventory["items"]["coverage"]["confirmation"] != "command"


def test_inventory_marks_missing_and_stale_evidence_fail_closed(tmp_path: Path):
    stale_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    inventory = build_inventory(
        tmp_path,
        command_evidence={
            "quality": {
                "status": "complete",
                "source": "make quality",
                "confirmation": "command",
                "evidence": ["target/quality.json"],
                "staleAt": stale_at,
            }
        },
    )

    quality = inventory["items"]["quality"]
    assert quality["status"] == "incomplete"
    assert quality["blockingReason"] == "evidence is stale"
    assert inventory["items"]["profile"]["status"] == "incomplete"
    assert inventory["items"]["profile"]["blockingReason"]


def test_template_boundary_is_not_reported_as_adopter_lifecycle_readiness(tmp_path: Path):
    (tmp_path / ".ai").mkdir()
    (tmp_path / ".ai" / "project_profile.yaml").write_text(
        "version: 1\nrepositoryRole: template\n",
        encoding="utf-8",
    )

    inventory = build_inventory(tmp_path)

    lifecycle = inventory["items"]["installed_lifecycle"]
    assert lifecycle["status"] == "not_applicable"
    assert lifecycle["confirmation"] == "static"
    assert "template" in lifecycle["blockingReason"]


def test_inventory_cli_writes_deterministic_json(tmp_path: Path, capsys):
    from ai_calibration_inventory import main

    output = tmp_path / "inventory.json"
    assert main(["--root", str(tmp_path), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == 1
    assert payload["items"]["documentation"]["source"]
    assert "calibration inventory written" in capsys.readouterr().out


def test_generated_status_renders_the_same_inventory_provenance(tmp_path: Path):
    inventory = build_inventory(tmp_path)
    model = {
        "recommendation": "needs_investigation",
        "signals": [],
        "evidence": {},
        "decisionDrivers": [],
    }
    status = render_active_status(
        model,
        work_item_id="inventory-test",
        mode="code",
        contract_path="contract.json",
        summary_path="summary.json",
        generated_at="<timestamp>",
        calibration_inventory=inventory,
    )
    assert "## Calibration Inventory" in status
    assert "profile:" in status
    assert "confirmation=`none`" in status
