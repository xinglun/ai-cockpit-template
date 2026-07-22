import json
import subprocess
from pathlib import Path


FIXTURE = Path(__file__).parents[1] / "examples" / "fixtures" / "typescript-web"


def run_npm(*args: str) -> str:
    result = subprocess.run(["npm", *args], cwd=FIXTURE, capture_output=True, text=True, check=True)
    return result.stdout


def test_typescript_fixture_executes_build_test_lint_and_format():
    run_npm("install", "--ignore-scripts", "--no-audit", "--no-fund")
    run_npm("run", "build")
    run_npm("test")
    run_npm("run", "lint")
    run_npm("run", "format:check")


def test_typescript_fixture_lifecycle_records_blocks_and_not_run_boundary():
    output = run_npm("run", "lifecycle")
    evidence = json.loads(output[output.index("{") :])
    assert {item["phase"] for item in evidence["phases"]} == {
        "Install",
        "Configure",
        "Normal Work Item",
        "Ambiguous Request",
        "Critical Domain Change",
        "Upgrade",
        "Rollback",
        "Release Check",
    }
    assert all(
        item["resumeCondition"] != "none"
        for item in evidence["phases"]
        if item["status"] == "blocked"
    )
    assert all(
        item["executionKind"] == "local_real_execution"
        for item in evidence["phases"]
        if item["status"] == "passed"
    )
    assert all(
        item["executionKind"] == "blocked"
        for item in evidence["phases"]
        if item["status"] == "blocked"
    )
    assert evidence["externalProviderEvidence"]["status"] == "not_run"
