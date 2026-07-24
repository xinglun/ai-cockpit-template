from pathlib import Path

import pytest

from ai_check_registry import CheckerRegistry, CheckResult
from ai_impact_classifier import classify_path
from ai_verify import evaluate_trend, run_verification, verify_stage
from ai_verification_context import build_context


def test_impact_classifier_covers_known_domains_and_unknown():
    assert classify_path("README.md") == "docs"
    assert classify_path("scripts/install_ai_cockpit.py") == "installer"
    assert classify_path(".ai/guards/file_ownership.yaml") == "trust"
    assert classify_path(".github/workflows/release.yml") == "release"
    assert classify_path("vendor/unexpected.bin") == "unknown"
    assert classify_path("tests/test_feature.py") == "tests"
    assert classify_path(".github/workflows/test.yml") == "workflow"
    assert classify_path("pyproject.toml") == "dependency"
    assert classify_path("src/app.py") == "project_code"
    assert classify_path("release.json") == "release"


def test_context_reads_each_input_once_and_is_immutable(tmp_path: Path):
    calls = []

    def read_json(path):
        calls.append(Path(path).name)
        return {"path": Path(path).name}

    def read_diff():
        calls.append("git")
        return ["README.md", "scripts/check.py"]

    context = build_context(
        tmp_path,
        "contract.json",
        "summary.json",
        read_json=read_json,
        read_diff=read_diff,
    )

    assert calls == ["contract.json", "summary.json", "git"]
    assert context.changed_paths == ("README.md", "scripts/check.py")
    with pytest.raises(TypeError):
        context.contract["new"] = True


def test_checker_registry_deduplicates_and_records_explicit_skip():
    registry = CheckerRegistry()
    registry.register("trust", lambda: CheckResult.passed("trust"))
    registry.register("trust", lambda: CheckResult.failed("trust"))

    results = registry.run(["trust", "trust", "release"], available={"trust"})

    assert results[0].status == "passed"
    assert results[1].status == "skipped"
    assert results[1].reason_code == "stage_not_applicable"
    assert len(registry.checker_ids) == 1


def test_release_stage_keeps_identity_failure_as_hard_gate():
    registry = CheckerRegistry()
    registry.register("identity", lambda: CheckResult.failed("identity", gate="hard"))

    results = verify_stage(object(), "release", registry)

    identity = next(result for result in results if result.checker_id == "identity")
    assert identity.status == "failed"
    assert identity.gate == "hard"


def test_complexity_warning_is_soft_and_not_green_claim():
    result = CheckResult.warning("complexity_trend", detail="insufficient samples")

    assert result.status == "warning"
    assert result.gate == "soft"


def test_result_validation_and_stage_validation_are_fail_closed():
    with pytest.raises(ValueError):
        CheckResult("x", "not-a-status")
    with pytest.raises(ValueError):
        CheckResult("x", "passed", "not-a-gate")
    with pytest.raises(ValueError):
        CheckResult("x", "skipped")
    with pytest.raises(ValueError):
        verify_stage(object(), "not-a-stage", CheckerRegistry())


def test_trend_requires_human_confirmation_when_threshold_is_exceeded():
    result = evaluate_trend("pythonLines", [10, 11, 20], threshold=2)

    assert result.status == "needs_human_confirmation"
    assert result.gate == "soft"
    assert result.reason_code == "threshold_exceeded"


def test_legacy_unified_and_compare_modes_are_explicit():
    registry = CheckerRegistry()
    registry.register("scope", lambda: CheckResult.passed("scope"))

    legacy = run_verification(object(), registry, mode="legacy")
    unified = run_verification(object(), registry, mode="unified")
    compare = run_verification(object(), registry, mode="compare")

    assert legacy["mode"] == "legacy"
    assert unified["mode"] == "unified"
    assert set(compare) == {"mode", "legacy", "unified"}
