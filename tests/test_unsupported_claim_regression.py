"""Regression coverage for unsupported external claims."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import unsupported_claim_gate  # noqa: E402


def test_gate_blocks_six_unsupported_claims_and_allows_supported_claim() -> None:
    report = unsupported_claim_gate.run_regression(ROOT)
    states = {item["name"]: item["state"] for item in report["results"]}
    assert all(states[name] == "blocked" for name in list(states)[:6])
    assert states["supported_claim"] == "allowed"
    for item in report["results"]:
        assert item["reason"]
        assert item["evidence"] is not None
        assert item["resumeCondition"]
        assert item["policyReference"] == "unsupported-claim-evidence-policy"


def test_gate_cli_is_an_enforced_local_regression_entrypoint() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/unsupported_claim_gate.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    assert report["gate"] == "Unsupported Claim Regression Gate"


def test_gate_handles_malformed_and_approved_structured_evidence() -> None:
    malformed = unsupported_claim_gate.evaluate_claim({"evidence": [None]}, root=ROOT)
    approved = unsupported_claim_gate.evaluate_claim(
        {
            "evidence": [
                {"kind": "approval", "approved": True, "path": "scripts/unsupported_claim_gate.py"}
            ]
        },
        root=ROOT,
    )
    assert malformed["state"] == "blocked"
    assert approved["state"] == "allowed"


def test_gate_cli_returns_failure_for_a_bad_regression(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        unsupported_claim_gate,
        "run_regression",
        lambda root: {"results": [{"name": "confident_without_evidence", "state": "allowed"}]},
    )
    assert unsupported_claim_gate.main() == 1
    assert "results" in capsys.readouterr().out
