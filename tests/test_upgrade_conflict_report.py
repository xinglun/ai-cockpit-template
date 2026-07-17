from ai_upgrade_conflict_report import build_report, validate_report


def test_report_classifies_human_confirmation_and_recommends_preservation():
    report = build_report(
        [
            {
                "path": ".ai/guards/custom.yaml",
                "classification": "Project-owned",
                "reason": "Target differs from template.",
            },
            {
                "path": "docs/local.md",
                "classification": "Human Confirmation Required",
                "reason": "Diverged managed file.",
            },
        ]
    )
    assert report["status"] == "needs_human_confirmation"
    assert report["requiresHumanConfirmation"] is True
    assert report["entries"][1]["recommendation"]
    assert validate_report(report) == []


def test_report_rejects_missing_path_and_invalid_classification():
    report = build_report([{"path": "x", "classification": "Template-owned"}])
    report["entries"].append({"classification": "Unknown"})
    issues = validate_report(report)
    assert "entries[1] must contain a path" in issues


def test_report_rejects_invalid_version_and_classification():
    report = build_report([{"path": "x", "classification": "Template-owned"}])
    report["reportVersion"] = 99
    report["entries"].append({"path": "y", "classification": "Unknown"})
    issues = validate_report(report)
    assert "reportVersion is unsupported" in issues
    assert "entries[1] has an invalid classification" in issues


def test_ready_report_does_not_require_confirmation():
    report = build_report([{"path": "x", "classification": "Template-owned"}])
    assert report["status"] == "ready"
    assert report["requiresHumanConfirmation"] is False


def test_missing_report_is_not_treated_as_valid():
    assert validate_report(None) == ["report must be an object"]
