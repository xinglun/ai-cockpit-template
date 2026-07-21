import json
import shutil
import subprocess

import ai_project_doctor


def fact_values(report, category):
    return {item["value"] for item in report["detectedFacts"][category]}


def test_doctor_detects_ios_layout_signals_without_auto_approval(tmp_path):
    (tmp_path / "Podfile").write_text("platform :ios, '15.0'\n", encoding="utf-8")
    (tmp_path / "MyApp.xcodeproj").mkdir()
    (tmp_path / "MyApp").mkdir()
    (tmp_path / "MyAppTests").mkdir()
    (tmp_path / "MyApp" / "AppDelegate.swift").write_text("import UIKit\n", encoding="utf-8")

    report = ai_project_doctor.scan_project(tmp_path)

    assert "cocoapods" in fact_values(report, "buildSystems")
    assert "xcode-project" in fact_values(report, "buildSystems")
    assert report["suggestedBoundaries"]["testRoots"][0]["evidence"] == "MyAppTests"
    assert (
        report["suggestedBoundaries"]["productionRoots"][0]["evidence"] == "MyApp.xcodeproj:MyApp"
    )
    assert report["disclaimer"].endswith("not approval decisions.")
    assert not any(item.startswith("blocking:") for item in report["unknowns"])


def test_doctor_detects_xcode_workspace_and_keeps_blocking_unknowns_without_roots(tmp_path):
    (tmp_path / "MyApp.xcworkspace").mkdir()
    (tmp_path / "Podfile").write_text("platform :ios, '15.0'\n", encoding="utf-8")

    report = ai_project_doctor.scan_project(tmp_path)

    assert "xcode-workspace" in fact_values(report, "buildSystems")
    assert any(item.startswith("blocking:") for item in report["unknowns"])


def test_doctor_detects_swift_package_manager_without_regression(tmp_path):
    (tmp_path / "Package.swift").write_text("// swift-tools-version:5.9\n", encoding="utf-8")
    (tmp_path / "Sources").mkdir()
    (tmp_path / "Tests").mkdir()

    report = ai_project_doctor.scan_project(tmp_path)

    assert "swift-package-manager" in fact_values(report, "buildSystems")
    assert report["suggestedBoundaries"]["productionRoots"][0]["evidence"] == "Sources"
    assert any(
        item["path"].lower() == "tests/**" for item in report["suggestedBoundaries"]["testRoots"]
    )
    assert report["unknowns"] == []


def test_doctor_ignores_untracked_virtualenv_files_in_git_repository(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'fixture'\n", encoding="utf-8")
    (tmp_path / ".venv" / "lib" / "python3.14" / "site-packages").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "python3.14" / "site-packages" / "coverage.js").write_text(
        "// ignored evidence\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", ".gitignore", "pyproject.toml"], cwd=tmp_path, check=True)

    report = ai_project_doctor.scan_project(tmp_path)

    assert fact_values(report, "languages") == {"python"}
    assert all(".venv" not in json.dumps(item) for item in report["detectedFacts"]["languages"])


def test_doctor_keeps_filesystem_fallback_for_non_git_fixture(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "app.py").write_text("def add(): pass\n", encoding="utf-8")

    report = ai_project_doctor.scan_project(tmp_path)

    assert "python" in fact_values(report, "languages")
    assert report["suggestedBoundaries"]["productionRoots"][0]["evidence"] == "src"


def test_doctor_surfaces_quality_commands_and_critical_domains(tmp_path):
    (tmp_path / "billing").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "Makefile").write_text("quality:\n", encoding="utf-8")

    report = ai_project_doctor.scan_project(tmp_path)

    assert report["projectSignals"]["qualityCommands"][0]["value"] == "make quality"
    assert report["projectSignals"]["criticalDomains"][0]["value"] == "billing"


def test_cockpit_doctor_uses_template_maintenance_context(tmp_path, monkeypatch):
    import ai_doctor

    shutil.copytree("templates", tmp_path / "templates")
    (tmp_path / ".ai" / "work-items" / "_templates").mkdir(parents=True)
    shutil.copytree(
        ".ai/work-items/_templates", tmp_path / ".ai/work-items/_templates", dirs_exist_ok=True
    )
    (tmp_path / ".ai" / "project_profile.yaml").parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(".ai/project_profile.yaml", tmp_path / ".ai/project_profile.yaml")
    monkeypatch.delenv("AI_COCKPIT_EXECUTION_MODE", raising=False)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Doctor Test",
            "-c",
            "user.email=doctor@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "initial",
        ],
        cwd=tmp_path,
        check=True,
    )

    _, warnings, failures = ai_doctor.diagnose(tmp_path)

    assert failures == []
    assert not any("adopted or unconfirmed template" in warning for warning in warnings)
