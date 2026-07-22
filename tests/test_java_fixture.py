"""Verify the Java multi-module fixture produces real, bounded local evidence."""

import json
import subprocess
from pathlib import Path


FIXTURE = Path(__file__).parents[1] / "examples/fixtures/java-multimodule"


def test_java_multimodule_lifecycle() -> None:
    result = subprocess.run(
        ["sh", "scripts/lifecycle.sh"],
        cwd=FIXTURE,
        check=True,
        text=True,
        capture_output=True,
    )
    evidence = json.loads(result.stdout)
    phases = {phase["name"]: phase for phase in evidence["phases"]}
    assert list(phases) == [
        "Install",
        "Configure",
        "Normal Work Item",
        "Ambiguous Request",
        "Critical Domain Change",
        "Upgrade",
        "Rollback",
        "Release Check",
    ]
    assert phases["Normal Work Item"]["status"] == "passed"
    assert phases["Normal Work Item"]["executionKind"] == "local_real_execution"
    assert phases["Ambiguous Request"]["status"] == "blocked"
    assert phases["Critical Domain Change"]["status"] == "blocked"
    assert phases["Ambiguous Request"]["resumeCondition"]
    assert phases["Critical Domain Change"]["resumeCondition"]
    assert phases["Ambiguous Request"]["executionKind"] == "blocked"
    assert phases["Critical Domain Change"]["executionKind"] == "blocked"
    assert phases["Upgrade"]["executionKind"] == "local_real_execution"
    assert phases["Rollback"]["executionKind"] == "local_real_execution"
    assert "provider release:not_run" in phases["Release Check"]["evidence"]


def test_java_fixture_declares_evidence_boundary() -> None:
    evidence = json.loads((FIXTURE / "evidence.json").read_text())
    assert "javac -Xlint:all" in evidence["executed"]
    assert "maven (unavailable locally)" in evidence["notRun"]
    assert "provider release" in evidence["notRun"]
    assert "only local Java source compilation" in evidence["claimBoundary"]
