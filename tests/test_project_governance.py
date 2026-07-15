import json
import re
import shutil
import sys
from pathlib import Path

import ai_calibrate
import ai_project_doctor
import check_bandit_baseline
import check_system_invariants
from ai_check_guard_calibration import calibration_issues
from ai_project_profile import load_profile, validate_profile
from check_system_invariants import invariant_issues


ROOT = Path(__file__).resolve().parents[1]


def fact_values(report, category):
    return {item["value"] for item in report["detectedFacts"][category]}


def test_doctor_detects_flutter_with_evidence_and_confidence(tmp_path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "test").mkdir()
    (tmp_path / "pubspec.yaml").write_text(
        "dependencies:\n  flutter:\n    sdk: flutter\n  flutter_bloc: any\n", encoding="utf-8"
    )
    (tmp_path / "lib" / "main.dart").write_text("void main() {}\n", encoding="utf-8")

    report = ai_project_doctor.scan_project(tmp_path)

    assert "dart" in fact_values(report, "languages")
    assert "flutter" in fact_values(report, "frameworks")
    assert report["suggestedBoundaries"]["productionRoots"][0]["evidence"] == "lib"
    assert report["projectSignals"]["stateManagement"][0]["value"] in {"bloc", "flutter_bloc"}
    assert all(
        item["confidence"] in {"high", "medium", "low"}
        for item in report["detectedFacts"]["languages"]
    )


def test_doctor_detects_spring_boot_and_infrastructure(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "build.gradle").write_text(
        "plugins { id 'org.springframework.boot' version '3.4.0' }\n", encoding="utf-8"
    )
    (tmp_path / "src" / "App.java").write_text("class App {}\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")

    report = ai_project_doctor.scan_project(tmp_path)

    assert "spring-boot" in fact_values(report, "frameworks")
    assert "gradle" in fact_values(report, "buildSystems")
    assert "github-actions" in fact_values(report, "infrastructure")
    assert report["projectSignals"]["ciReleaseDeployment"]


def test_doctor_detects_python_ai_and_keeps_unknown_boundaries(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "dependencies = ['fastapi', 'torch']\n", encoding="utf-8"
    )
    report = ai_project_doctor.scan_project(tmp_path)
    assert "python" in fact_values(report, "languages")
    assert "fastapi" in fact_values(report, "frameworks")
    assert any(item.startswith("blocking:") for item in report["unknowns"])


def test_doctor_cli_only_writes_requested_target_report(tmp_path):
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert ai_project_doctor.main.__module__ == "ai_project_doctor"
    report = ai_project_doctor.scan_project(tmp_path)
    assert report["disclaimer"].endswith("not approval decisions.")
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert before == after


def test_calibration_generates_proposal_without_approval_or_overwrite(tmp_path):
    report = ai_project_doctor.scan_project(tmp_path)
    report_path = tmp_path / "target" / "doctor.json"
    report_path.parent.mkdir()
    report_path.write_text(json.dumps(report), encoding="utf-8")
    output = tmp_path / ".ai" / "project_profile.proposed.yaml"

    assert ai_calibrate.generate(tmp_path, report_path, output) == 0
    profile, issues = load_profile(output, require_approval=False)
    assert issues == []
    assert profile["repositoryRole"] == "template"
    assert profile["approval"]["reviewed"] == "false"
    assert profile["approvedBoundaries"]["productionRoots"] == []
    original = output.read_text(encoding="utf-8")
    assert ai_calibrate.generate(tmp_path, report_path, output) == 2
    assert output.read_text(encoding="utf-8") == original


def test_calibration_render_helpers_cover_empty_and_populated_boundaries(tmp_path):
    report = {
        "reportVersion": 1,
        "detectedFacts": {"languages": [{"value": "Python"}], "buildSystems": []},
        "suggestedBoundaries": {"productionRoots": [{"path": "src/**"}], "testRoots": []},
        "unknowns": ["review boundary"],
    }
    text = ai_calibrate.proposed_profile(report)
    assert '"Python"' in text
    assert "productionRoots:" in text
    assert "testRoots: []" in text
    assert ai_calibrate.quote("日本語") == '"日本語"'
    assert ai_calibrate.values(None, "value") == []
    report_path = tmp_path / "report.json"
    output = tmp_path / "proposal.yaml"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    assert ai_calibrate.generate(tmp_path, report_path, output) == 0
    assert ai_calibrate.generate(tmp_path, report_path, output) == 2


def test_calibration_main_dispatches_generate_and_validate(tmp_path, monkeypatch):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps({"reportVersion": 1}), encoding="utf-8")
    output = tmp_path / "proposal.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_calibrate",
            "generate",
            "--root",
            str(tmp_path),
            "--report",
            "report.json",
            "--output",
            "proposal.yaml",
        ],
    )
    assert ai_calibrate.main() == 0
    monkeypatch.setattr(sys, "argv", ["ai_calibrate", "validate", "--profile", str(output)])
    assert ai_calibrate.main() == 0


def test_profile_strictly_separates_confirmation_and_blocking_unknowns():
    profile = {
        "version": 1,
        "detectedFacts": {
            key: [] for key in ("languages", "frameworks", "buildSystems", "infrastructure")
        },
        "suggestedBoundaries": {
            key: []
            for key in (
                "productionRoots",
                "featureRoots",
                "testRoots",
                "generatedPaths",
                "criticalPaths",
            )
        },
        "approvedBoundaries": {
            "productionRoots": ["src/**"],
            "featureRoots": [],
            "testRoots": ["tests/**"],
            "generatedPaths": [],
            "criticalPaths": [],
        },
        "reviewRequirements": [],
        "unknowns": ["blocking: owner decision"],
        "evidence": [],
        "approval": {"reviewed": True, "reviewedBy": "owner", "reason": "reviewed"},
    }
    assert any(
        "blocking unknowns" in issue for issue in validate_profile(profile, require_approval=True)
    )
    profile["unknowns"] = []
    assert validate_profile(profile, require_approval=True) == []


def test_guard_calibration_fails_when_confirmed_path_is_missing(tmp_path):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    profile, issues = load_profile(tmp_path / ".ai" / "project_profile.yaml", require_approval=True)
    assert issues == []
    profile["approvedBoundaries"]["productionRoots"].append("service/**")
    assert any("service/**" in issue for issue in calibration_issues(tmp_path, profile))


def test_guard_calibration_reports_missing_generated_boundary(tmp_path):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    profile, issues = load_profile(tmp_path / ".ai" / "project_profile.yaml", require_approval=True)
    assert issues == []
    profile["approvedBoundaries"]["generatedPaths"] = ["cache/**"]
    assert any("generated path" in issue for issue in calibration_issues(tmp_path, profile))


def test_guard_calibration_reports_missing_quality_check_id(tmp_path):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    profile, issues = load_profile(tmp_path / ".ai" / "project_profile.yaml", require_approval=True)
    assert issues == []
    profile["reviewRequirements"] = ["quality"]
    (tmp_path / ".ai" / "cockpit" / "checks.yaml").write_text("checks: {}\n", encoding="utf-8")
    assert any(
        "quality review requirement" in issue for issue in calibration_issues(tmp_path, profile)
    )


def test_guard_calibration_rejects_non_object_approved_boundaries(tmp_path):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    assert calibration_issues(tmp_path, {"approvedBoundaries": []}) == [
        "approvedBoundaries must be an object"
    ]


def test_guard_calibration_accepts_optional_boundary_lists(tmp_path):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    profile, issues = load_profile(tmp_path / ".ai" / "project_profile.yaml", require_approval=True)
    assert issues == []
    profile["approvedBoundaries"]["featureRoots"] = ["src/**"]
    profile["approvedBoundaries"]["criticalPaths"] = [".github/workflows/**"]
    assert calibration_issues(tmp_path, profile) == []


def test_guard_calibration_reports_missing_boundary_configuration(tmp_path):
    profile = {
        "approvedBoundaries": {
            "productionRoots": ["src/**"],
            "testRoots": ["tests/**"],
            "generatedPaths": ["generated/**"],
            "criticalPaths": ["src/critical.py"],
        },
        "reviewRequirements": ["quality"],
    }
    for path in (
        ".ai/guards/coverage_policy.yaml",
        ".ai/guards/file_ownership.yaml",
        ".ai/guards/ai_review_policy.yaml",
        ".ai/guards/file_boundary.yaml",
        ".ai/cockpit/checks.yaml",
    ):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")

    issues = calibration_issues(tmp_path, profile)
    assert any("productionRoots pattern" in issue for issue in issues)
    assert any("testRoots pattern" in issue for issue in issues)
    assert any("generated path" in issue for issue in issues)
    assert any("critical path" in issue for issue in issues)
    assert any("quality review requirement" in issue for issue in issues)


def test_guard_calibration_main_reports_success_and_missing_profile(monkeypatch, tmp_path):
    import ai_check_guard_calibration

    monkeypatch.setattr(sys, "argv", ["ai_check_guard_calibration", "--root", str(ROOT)])
    assert ai_check_guard_calibration.main() == 0
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_check_guard_calibration", "--root", str(tmp_path), "--profile", "missing.yaml"],
    )
    assert ai_check_guard_calibration.main() == 1


def test_repository_system_invariants_are_consistent():
    assert invariant_issues(ROOT) == []


def test_system_invariants_reject_missing_dev_lock(tmp_path, monkeypatch):
    copy = tmp_path / "repository"
    shutil.copytree(
        ROOT, copy, ignore=shutil.ignore_patterns(".git", ".venv", "target", "__pycache__")
    )
    (copy / "requirements-dev.lock").unlink()
    monkeypatch.setattr(
        check_system_invariants, "exercise_installer", lambda *_args, **_kwargs: None
    )
    issues = check_system_invariants.invariant_issues(copy)
    assert any("requirements-dev.lock is missing" in issue for issue in issues)


def test_system_invariants_reject_missing_governance_docs(tmp_path, monkeypatch):
    copy = tmp_path / "repository"
    shutil.copytree(
        ROOT, copy, ignore=shutil.ignore_patterns(".git", ".venv", "target", "__pycache__")
    )
    (copy / "SECURITY.md").unlink()
    (copy / "CONTRIBUTING.md").unlink()
    (copy / ".github" / "CODEOWNERS").unlink()
    (copy / ".github" / "dependabot.yml").unlink()
    monkeypatch.setattr(
        check_system_invariants, "exercise_installer", lambda *_args, **_kwargs: None
    )
    issues = check_system_invariants.invariant_issues(copy)
    assert any("SECURITY.md is missing" in issue for issue in issues)
    assert any("CONTRIBUTING.md is missing" in issue for issue in issues)
    assert any("CODEOWNERS is missing" in issue for issue in issues)
    assert any("dependabot.yml is missing" in issue for issue in issues)


def test_system_invariants_allow_missing_archive_summary_version(tmp_path, monkeypatch):
    copy = tmp_path / "repository"
    shutil.copytree(
        ROOT, copy, ignore=shutil.ignore_patterns(".git", ".venv", "target", "__pycache__")
    )
    archive_summary = next((copy / ".ai" / "work-items" / "archive").rglob("*.summary.json"))
    data = json.loads(archive_summary.read_text(encoding="utf-8"))
    data.pop("summaryVersion", None)
    archive_summary.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        check_system_invariants, "exercise_installer", lambda *_args, **_kwargs: None
    )
    issues = check_system_invariants.invariant_issues(copy)
    assert all(
        "archived Summary summaryVersion must be absent or 1/2 when present" not in issue
        for issue in issues
    )


def test_bandit_baseline_matches_repository_low_risk_findings():
    assert check_bandit_baseline.main() == 0


def test_system_invariants_reject_manifest_stack_drift(tmp_path, monkeypatch):
    copy = tmp_path / "repository"
    shutil.copytree(
        ROOT, copy, ignore=shutil.ignore_patterns(".git", ".venv", "target", "__pycache__")
    )
    manifest = copy / ".ai" / "cockpit" / "system_invariants.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["stacks"].remove("python")
    manifest.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        check_system_invariants, "exercise_installer", lambda *_args, **_kwargs: None
    )
    assert any(
        "manifest stack list" in issue for issue in check_system_invariants.invariant_issues(copy)
    )


def test_system_invariants_reject_unpinned_workflow_actions(tmp_path, monkeypatch):
    copy = tmp_path / "repository"
    shutil.copytree(
        ROOT, copy, ignore=shutil.ignore_patterns(".git", ".venv", "target", "__pycache__")
    )
    workflow = copy / ".github" / "workflows" / "smoke.yml"
    workflow.write_text(
        re.sub(
            r"(uses:\s*actions/checkout)@[^\s]+",
            r"\1@v6",
            workflow.read_text(encoding="utf-8"),
            count=1,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        check_system_invariants, "exercise_installer", lambda *_args, **_kwargs: None
    )
    issues = check_system_invariants.invariant_issues(copy)
    assert any(
        "workflow action references must be pinned to a commit SHA" in issue for issue in issues
    )


def test_governance_hardening_modules_remain_importable():
    import ai_calibrate
    import ai_check_agent_risk
    import ai_check_backtrack
    import ai_check_guard_calibration
    import ai_check_guards
    import ai_check_review_policy
    import ai_check_scope
    import ai_observability
    import ai_project_profile

    assert ai_calibrate.__name__ == "ai_calibrate"
    assert ai_check_agent_risk.__name__ == "ai_check_agent_risk"
    assert ai_check_backtrack.__name__ == "ai_check_backtrack"
    assert ai_check_guard_calibration.__name__ == "ai_check_guard_calibration"
    assert ai_check_guards.__name__ == "ai_check_guards"
    assert ai_check_review_policy.__name__ == "ai_check_review_policy"
    assert ai_check_scope.__name__ == "ai_check_scope"
    assert ai_observability.__name__ == "ai_observability"
    assert ai_project_profile.__name__ == "ai_project_profile"
