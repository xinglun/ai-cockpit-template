import json
import subprocess
import sys
from pathlib import Path

import cross_stack_long_cycle


ROOT = Path(__file__).resolve().parents[1]


def test_cross_stack_bundle_covers_all_fixture_phases_and_boundaries():
    bundle = cross_stack_long_cycle.run(ROOT)
    assert {item["stack"] for item in bundle["fixtures"]} == {
        "python",
        "java-multimodule",
        "typescript-web",
    }
    assert bundle["adopterRepository"]["remote"] == "local bare origin"
    assert bundle["adopterRepository"]["remoteBranchesCleaned"] is True
    assert bundle["evidenceBoundary"]["providerEvidence"] == "not_run"
    phases = {phase["phase"] for fixture in bundle["fixtures"] for phase in fixture["phases"]}
    assert "Critical Domain Change" in phases
    assert "Release Check" in phases


def test_cross_stack_cli_writes_json(tmp_path):
    output = tmp_path / "bundle.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "cross_stack_long_cycle.py"),
            "--root",
            str(ROOT),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["schemaVersion"] == 1
    assert (
        json.loads(output.read_text(encoding="utf-8"))["adopterRepository"]["localBranchesCleaned"]
        is True
    )
