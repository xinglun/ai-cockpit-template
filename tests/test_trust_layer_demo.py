import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_trust_layer_demo_records_required_stops_and_safe_continuation():
    result = subprocess.run(
        [str(ROOT / "docs/examples/trust-layer-demo.sh")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    records = [json.loads(line) for line in result.stdout.splitlines()]
    scenarios = {record["scenario"]: record for record in records[:-1]}
    assert set(scenarios) == {
        "unclear-rocket-intent",
        "chinese-dangerous-expression",
        "scope-disguise",
        "stale-decision-evidence",
        "normal-low-risk-request",
    }
    for scenario in list(scenarios)[:4]:
        assert scenarios[scenario]["status"] == "not_ready"
        assert scenarios[scenario]["decision"] == "stop"
        assert scenarios[scenario]["resumeCondition"]
        assert scenarios[scenario]["governancePath"]
    assert scenarios["normal-low-risk-request"]["status"] == "ready"
    assert records[-1]["summary"]["unsafeOperations"] == 0
