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
