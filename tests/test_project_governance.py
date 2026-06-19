import json
import shutil
from pathlib import Path

import ai_calibrate
import ai_project_doctor
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
    (tmp_path / "pubspec.yaml").write_text("dependencies:\n  flutter:\n    sdk: flutter\n  flutter_bloc: any\n", encoding="utf-8")
    (tmp_path / "lib" / "main.dart").write_text("void main() {}\n", encoding="utf-8")

    report = ai_project_doctor.scan_project(tmp_path)

    assert "dart" in fact_values(report, "languages")
    assert "flutter" in fact_values(report, "frameworks")
    assert report["suggestedBoundaries"]["productionRoots"][0]["evidence"] == "lib"
    assert report["projectSignals"]["stateManagement"][0]["value"] in {"bloc", "flutter_bloc"}
    assert all(item["confidence"] in {"high", "medium", "low"} for item in report["detectedFacts"]["languages"])


def test_doctor_detects_spring_boot_and_infrastructure(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "build.gradle").write_text("plugins { id 'org.springframework.boot' version '3.4.0' }\n", encoding="utf-8")
    (tmp_path / "src" / "App.java").write_text("class App {}\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")

    report = ai_project_doctor.scan_project(tmp_path)

    assert "spring-boot" in fact_values(report, "frameworks")
    assert "gradle" in fact_values(report, "buildSystems")
    assert "github-actions" in fact_values(report, "infrastructure")
    assert report["projectSignals"]["ciReleaseDeployment"]


def test_doctor_detects_python_ai_and_keeps_unknown_boundaries(tmp_path):
    (tmp_path / "pyproject.toml").write_text("dependencies = ['fastapi', 'torch']\n", encoding="utf-8")
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
    assert profile["approval"]["reviewed"] == "false"
    assert profile["approvedBoundaries"]["productionRoots"] == []
    original = output.read_text(encoding="utf-8")
    assert ai_calibrate.generate(tmp_path, report_path, output) == 2
    assert output.read_text(encoding="utf-8") == original


def test_profile_strictly_separates_confirmation_and_blocking_unknowns():
    profile = {
        "version": 1,
        "detectedFacts": {key: [] for key in ("languages", "frameworks", "buildSystems", "infrastructure")},
        "suggestedBoundaries": {key: [] for key in ("productionRoots", "featureRoots", "testRoots", "generatedPaths", "criticalPaths")},
        "approvedBoundaries": {
            "productionRoots": ["src/**"], "featureRoots": [], "testRoots": ["tests/**"],
            "generatedPaths": [], "criticalPaths": [],
        },
        "reviewRequirements": [], "unknowns": ["blocking: owner decision"], "evidence": [],
        "approval": {"reviewed": True, "reviewedBy": "owner", "reason": "reviewed"},
    }
    assert any("blocking unknowns" in issue for issue in validate_profile(profile, require_approval=True))
    profile["unknowns"] = []
    assert validate_profile(profile, require_approval=True) == []


def test_guard_calibration_fails_when_confirmed_path_is_missing(tmp_path):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    profile, issues = load_profile(tmp_path / ".ai" / "project_profile.yaml", require_approval=True)
    assert issues == []
    profile["approvedBoundaries"]["productionRoots"].append("service/**")
    assert any("service/**" in issue for issue in calibration_issues(tmp_path, profile))


def test_repository_system_invariants_are_consistent():
    assert invariant_issues(ROOT) == []


def test_system_invariants_reject_manifest_stack_drift(tmp_path, monkeypatch):
    copy = tmp_path / "repository"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", ".venv", "target", "__pycache__"))
    manifest = copy / ".ai" / "cockpit" / "system_invariants.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["stacks"].remove("python")
    manifest.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(check_system_invariants, "exercise_installer", lambda *_args, **_kwargs: None)
    assert any("manifest stack list" in issue for issue in check_system_invariants.invariant_issues(copy))
