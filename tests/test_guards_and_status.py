import json
from pathlib import Path

import ai_check_backtrack
import ai_check_coverage_guard
import ai_checkpoint
import ai_generate_status


ROOT = Path(__file__).resolve().parents[1]


def test_backtrack_detects_deleted_test_and_work_item():
    items = ai_check_backtrack.detect_items([
        ("D", "tests/unit_test.py"),
        ("D", ".ai/work-items/archive/2026/task.summary.json"),
    ])
    assert {item.kind for item in items} == {"deleted_test", "removed_work_item_record"}


def test_coverage_detects_production_change_without_test(tmp_path, monkeypatch):
    policy = tmp_path / "coverage.yaml"
    policy.write_text(
        "production:\n  include:\n    - src/**\ntests:\n  include:\n    - tests/**\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_coverage_guard, "POLICY", policy)
    assert ai_check_coverage_guard.detect(["src/service.py"])
    assert ai_check_coverage_guard.detect(["src/service.py", "tests/test_service.py"]) == []


def test_default_coverage_policy_covers_advertised_stack_layouts(monkeypatch):
    monkeypatch.setattr(ai_check_coverage_guard, "POLICY", ROOT / ".ai" / "guards" / "coverage_policy.yaml")
    production_paths = [
        "app/src/main/kotlin/com/example/Feature.kt",
        "Sources/App/Feature.swift",
        "MyApp/Services/Feature.cs",
        "src/main/java/com/example/Feature.java",
        "lib/feature.dart",
        "Program.cs",
        "app.go",
        "index.ts",
        "packages/web/src/index.ts",
        "services/api/src/main/java/com/example/App.java",
        "packages/ui/lib/widget.dart",
    ]
    for path in production_paths:
        assert ai_check_coverage_guard.detect([path]), path


def test_default_coverage_policy_recognizes_stack_test_layouts(monkeypatch):
    monkeypatch.setattr(ai_check_coverage_guard, "POLICY", ROOT / ".ai" / "guards" / "coverage_policy.yaml")
    cases = [
        ("app/src/main/kotlin/Feature.kt", "app/src/test/kotlin/FeatureTest.kt"),
        ("Sources/App/Feature.swift", "Tests/AppTests/FeatureTests.swift"),
        ("MyApp/Services/Feature.cs", "MyApp.Tests/FeatureTests.cs"),
        ("app.go", "app_test.go"),
        ("Program.cs", "ProgramTests.cs"),
        ("index.ts", "index.test.ts"),
        ("packages/web/src/index.ts", "packages/web/tests/index.test.ts"),
        ("services/api/src/main/java/App.java", "services/api/src/test/java/AppTest.java"),
        ("packages/ui/lib/widget.dart", "packages/ui/test/widget_test.dart"),
    ]
    for production, test in cases:
        assert ai_check_coverage_guard.detect([production, test]) == []


def test_checkpoint_next_action_stops_on_unknowns():
    contract = {"notCodable": False, "unknowns": ["decision"], "verification": []}
    assert ai_checkpoint.next_action(contract, None).startswith("Stop coding")


def test_retry_circuit_breaker_counts_consecutive_failures(tmp_path):
    log = tmp_path / "events.jsonl"
    events = [
        {"workItemId": "task", "eventType": "check_passed"},
        {"workItemId": "task", "eventType": "check_failed"},
        {"workItemId": "task", "eventType": "check_failed"},
    ]
    log.write_text("\n".join(json.dumps(item) for item in events) + "\n", encoding="utf-8")
    assert ai_generate_status.consecutive_failure_count("task", log) == 2
    state, blockers = ai_generate_status.status_for(
        {"workItemId": "task", "notCodable": False, "unknowns": [], "verification": []},
        {"verification": []},
        retry_threshold=2,
        observability_log=log,
    )
    assert state == "blocked_by_ai_loop"
    assert blockers


def test_project_relative_accepts_relative_repository_path():
    path = Path(".ai/work-items/active/task.contract.json")
    assert ai_generate_status.project_relative(path) == path.as_posix()


def test_generate_active_status_renders_evidence_and_backtrack(tmp_path, monkeypatch):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    output = tmp_path / "status.md"
    backtrack = tmp_path / "backtrack.json"
    contract.write_text(json.dumps({
        "workItemId": "task",
        "mode": "code",
        "notCodable": False,
        "unknowns": [],
        "verification": [{"check": "quality", "required": True}],
    }), encoding="utf-8")
    summary.write_text(json.dumps({
        "verification": [{"check": "quality", "result": "passed"}],
        "changedFiles": [{"path": "src/app.py", "reason": "feature"}],
    }), encoding="utf-8")
    backtrack.write_text(json.dumps({
        "status": "passed",
        "items": [{"kind": "test", "path": "tests/test_app.py", "detail": "present"}],
    }), encoding="utf-8")
    monkeypatch.setattr(ai_generate_status, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_generate_status, "BACKTRACK_REPORT", backtrack)
    monkeypatch.setattr(
        ai_generate_status,
        "create_observability",
        lambda **_kwargs: type("Obs", (), {"status_generated": lambda *_args, **_kwargs: None})(),
    )

    ai_generate_status.write_active_status(contract, summary, output=output, observability_log=tmp_path / "events.jsonl")
    text = output.read_text(encoding="utf-8")
    assert "ready_for_review" in text
    assert "`quality`: passed" in text
    assert "`src/app.py`: feature" in text
    assert "test: `tests/test_app.py` - present" in text


def test_generate_status_main_handles_no_active_and_invalid_contract(tmp_path, monkeypatch):
    output = tmp_path / "status.md"
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        ["ai_generate_status.py", "--no-active", "--output", str(output)],
    )
    assert ai_generate_status.main() == 0
    assert "no_active_work_item" in output.read_text(encoding="utf-8")

    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    monkeypatch.setattr(__import__("sys"), "argv", ["ai_generate_status.py", str(broken), "--output", str(output)])
    assert ai_generate_status.main() == 1
