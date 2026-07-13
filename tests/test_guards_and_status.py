import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import ai_check_backtrack
import ai_check_coverage_guard
import ai_check_status_consistency
import ai_checkpoint
import ai_generate_status
import ai_preflight_review


ROOT = Path(__file__).resolve().parents[1]


def test_backtrack_detects_deleted_test_and_work_item():
    items = ai_check_backtrack.detect_items(
        [
            ("D", "tests/unit_test.py"),
            ("D", ".ai/work-items/archive/2026/task.summary.json"),
        ]
    )
    assert {item.kind for item in items} == {"deleted_test", "removed_work_item_record"}


def test_coverage_detects_production_change_without_test(tmp_path, monkeypatch):
    policy = tmp_path / "coverage.yaml"
    policy.write_text(
        "production:\n  include:\n    - src/**\n"
        "tests:\n  include:\n    - tests/**\n"
        "associations:\n  service:\n    production:\n      - src/service.py\n"
        "    tests:\n      - tests/test_{stem}.py\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_coverage_guard, "POLICY", policy)
    assert ai_check_coverage_guard.detect(["src/service.py"])
    assert ai_check_coverage_guard.detect(["src/service.py", "tests/test_service.py"]) == []


def test_coverage_rejects_unrelated_test_change(tmp_path, monkeypatch):
    policy = tmp_path / "coverage.yaml"
    policy.write_text(
        "production:\n  include:\n    - src/**\n"
        "tests:\n  include:\n    - tests/**\n"
        "associations:\n  modules:\n    production:\n      - src/**\n"
        "    tests:\n      - tests/test_{stem}.py\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_coverage_guard, "POLICY", policy)

    items = ai_check_coverage_guard.detect(["src/auth.py", "tests/test_payment.py"])
    assert [item.path for item in items] == ["src/auth.py"]
    assert "configured association" in items[0].detail


def test_coverage_rejects_production_without_association(tmp_path, monkeypatch):
    policy = tmp_path / "coverage.yaml"
    policy.write_text(
        "production:\n  include:\n    - src/**\ntests:\n  include:\n    - tests/**\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_coverage_guard, "POLICY", policy)

    items = ai_check_coverage_guard.detect(["src/auth.py", "tests/test_auth.py"])
    assert "no associations.*.production rule" in items[0].detail


def test_default_coverage_policy_covers_advertised_stack_layouts(monkeypatch):
    monkeypatch.setattr(
        ai_check_coverage_guard, "POLICY", ROOT / ".ai" / "guards" / "coverage_policy.yaml"
    )
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
    monkeypatch.setattr(
        ai_check_coverage_guard, "POLICY", ROOT / ".ai" / "guards" / "coverage_policy.yaml"
    )
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


def test_default_coverage_policy_rejects_cross_module_test(monkeypatch):
    monkeypatch.setattr(
        ai_check_coverage_guard, "POLICY", ROOT / ".ai" / "guards" / "coverage_policy.yaml"
    )
    items = ai_check_coverage_guard.detect(["src/auth.rs", "tests/payment_test.rs"])
    assert [item.path for item in items] == ["src/auth.rs"]


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
    assert state == "blocked"
    assert blockers == ["retry circuit breaker: consecutive check failures 2/2"]


def test_project_relative_accepts_relative_repository_path():
    path = Path(".ai/work-items/active/task.contract.json")
    assert ai_generate_status.project_relative(path) == path.as_posix()


def test_generate_active_status_renders_evidence_and_backtrack(tmp_path, monkeypatch):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    output = tmp_path / "status.md"
    backtrack = tmp_path / "backtrack.json"
    contract.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "mode": "code",
                "notCodable": False,
                "unknowns": [],
                "acceptance": ["done"],
                "riskAssessment": {"level": "low", "riskTypes": [], "reason": "fixture"},
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(
        json.dumps(
            {
                "reviewReadiness": {
                    "status": "ready",
                    "reason": "fixture",
                    "expectedReviewFocus": [],
                },
                "verification": [{"check": "quality", "result": "passed"}],
                "unknownsRemaining": [],
                "risk": {"level": "low", "detail": "fixture"},
                "guidelinesCompliance": [],
                "checkpointEvidence": [],
                "residualRisks": [],
            }
        ),
        encoding="utf-8",
    )
    backtrack.write_text(
        json.dumps(
            {
                "status": "passed",
                "items": [{"kind": "test", "path": "tests/test_app.py", "detail": "present"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_generate_status, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_generate_status, "BACKTRACK_REPORT", backtrack)
    monkeypatch.setattr(ai_generate_status, "ownership_preview", lambda **_kwargs: [])
    monkeypatch.setattr(
        ai_generate_status,
        "create_observability",
        lambda **_kwargs: type("Obs", (), {"status_generated": lambda *_args, **_kwargs: None})(),
    )

    ai_generate_status.write_active_status(
        contract, summary, output=output, observability_log=tmp_path / "events.jsonl"
    )
    text = output.read_text(encoding="utf-8")
    assert "Recommendation: `ready_for_review`" in text
    assert "## Governance Signals" in text
    assert "## Evidence" in text
    assert "Verification: `quality: passed`" in text
    assert "Backtrack" in text
    assert "test: `tests/test_app.py` - present" in text


def test_generate_active_status_demotes_ready_for_review_when_ownership_is_unresolved(
    tmp_path, monkeypatch
):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    output = tmp_path / "status.md"
    contract.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "mode": "code",
                "notCodable": False,
                "unknowns": [],
                "acceptance": ["done"],
                "riskAssessment": {"level": "low", "riskTypes": [], "reason": "fixture"},
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(
        json.dumps(
            {
                "reviewReadiness": {
                    "status": "ready",
                    "reason": "fixture",
                    "expectedReviewFocus": [],
                },
                "verification": [{"check": "quality", "result": "passed"}],
                "unknownsRemaining": [],
                "risk": {"level": "low", "detail": "fixture"},
                "guidelinesCompliance": [],
                "checkpointEvidence": [],
                "residualRisks": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ai_generate_status, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ai_generate_status,
        "ownership_preview",
        lambda **_kwargs: [SimpleNamespace(path="src/app.py", state="unowned")],
    )
    monkeypatch.setattr(
        ai_generate_status,
        "create_observability",
        lambda **_kwargs: type("Obs", (), {"status_generated": lambda *_args, **_kwargs: None})(),
    )

    ai_generate_status.write_active_status(
        contract, summary, output=output, observability_log=tmp_path / "events.jsonl"
    )
    text = output.read_text(encoding="utf-8")

    assert "Recommendation: `needs_investigation`" in text
    assert "State: `needs_investigation`" in text
    assert "diff ownership unresolved: 1" in text


def test_generate_active_status_keeps_ready_for_review_when_ownership_is_clean(
    tmp_path, monkeypatch
):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    output = tmp_path / "status.md"
    contract.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "mode": "code",
                "notCodable": False,
                "unknowns": [],
                "acceptance": ["done"],
                "riskAssessment": {"level": "low", "riskTypes": [], "reason": "fixture"},
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(
        json.dumps(
            {
                "reviewReadiness": {
                    "status": "ready",
                    "reason": "fixture",
                    "expectedReviewFocus": [],
                },
                "verification": [{"check": "quality", "result": "passed"}],
                "unknownsRemaining": [],
                "risk": {"level": "low", "detail": "fixture"},
                "guidelinesCompliance": [],
                "checkpointEvidence": [],
                "residualRisks": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ai_generate_status, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ai_generate_status,
        "ownership_preview",
        lambda **_kwargs: [SimpleNamespace(path="src/app.py", state="active_owned")],
    )
    monkeypatch.setattr(
        ai_generate_status,
        "create_observability",
        lambda **_kwargs: type("Obs", (), {"status_generated": lambda *_args, **_kwargs: None})(),
    )

    ai_generate_status.write_active_status(
        contract, summary, output=output, observability_log=tmp_path / "events.jsonl"
    )
    text = output.read_text(encoding="utf-8")

    assert "Recommendation: `ready_for_review`" in text
    assert "State: `ready_for_review`" in text
    assert "diff ownership unresolved" not in text


def test_generate_active_status_includes_latest_preflight_review(tmp_path, monkeypatch):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    output = tmp_path / "status.md"
    contract.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "mode": "code",
                "notCodable": False,
                "unknowns": [],
                "acceptance": ["done"],
                "riskAssessment": {
                    "level": "medium",
                    "riskTypes": ["governance"],
                    "reason": "fixture",
                },
                "sources": [{"path": "docs/design.md", "reason": "fixture"}],
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(
        json.dumps(
            {
                "reviewReadiness": {
                    "status": "ready",
                    "reason": "fixture",
                    "expectedReviewFocus": [],
                },
                "verification": [{"check": "quality", "result": "passed"}],
                "unknownsRemaining": [],
                "risk": {"level": "medium", "detail": "fixture"},
                "guidelinesCompliance": [],
                "checkpointEvidence": [],
                "residualRisks": [],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "preflight_review_policy.yaml").write_text(
        "version: 1\ngateEnabled: false\nblockedStatuses: []\n",
        encoding="utf-8",
    )
    preflight = ai_preflight_review.derive_report(
        {
            "workItemId": "task",
            "mode": "code",
            "scope": ["src/**"],
            "outOfScope": ["docs/**"],
            "intent": {},
            "unknowns": ["gap"],
            "acceptance": ["Clarify required scenarios before implementation."],
            "sources": [{"path": "docs/design.md", "reason": "fixture"}],
            "scenarioCoverage": [],
            "verification": [{"check": "quality", "required": True}],
            "riskAssessment": {"level": "medium", "riskTypes": ["governance"], "reason": "fixture"},
        },
        contract_path=contract,
        policy_path=tmp_path / "preflight_review_policy.yaml",
    )
    preflight["workItemId"] = "task"
    preflight["contractHash"] = hashlib.sha256(contract.read_bytes()).hexdigest()[:16]
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "ai_preflight_review.json").write_text(
        json.dumps(preflight, indent=2) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(ai_generate_status, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_generate_status, "BACKTRACK_REPORT", tmp_path / "backtrack.json")
    monkeypatch.setattr(ai_generate_status, "ownership_preview", lambda **_kwargs: [])
    monkeypatch.setattr(
        ai_generate_status,
        "create_observability",
        lambda **_kwargs: type("Obs", (), {"status_generated": lambda *_args, **_kwargs: None})(),
    )

    ai_generate_status.write_active_status(
        contract, summary, output=output, observability_log=tmp_path / "events.jsonl"
    )
    text = output.read_text(encoding="utf-8")
    assert "## Preflight Review" in text
    assert "Status: `needs_human_confirmation`" in text
    assert "Recommendation: `Clarify intent before implementation.`" in text
    assert "Cockpit Status keeps the Preflight Review visible for reviewers" in text


def test_generate_active_status_ignores_output_path_in_ownership_counts(tmp_path, monkeypatch):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    output = tmp_path / ".ai" / "cockpit" / "current_status.md"
    contract.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "mode": "code",
                "notCodable": False,
                "unknowns": [],
                "acceptance": ["done"],
                "riskAssessment": {"level": "low", "riskTypes": [], "reason": "fixture"},
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(
        json.dumps(
            {
                "reviewReadiness": {
                    "status": "ready",
                    "reason": "fixture",
                    "expectedReviewFocus": [],
                },
                "verification": [{"check": "quality", "result": "passed"}],
                "unknownsRemaining": [],
                "risk": {"level": "low", "detail": "fixture"},
                "guidelinesCompliance": [],
                "checkpointEvidence": [],
                "residualRisks": [],
            }
        ),
        encoding="utf-8",
    )

    captured = {}

    def fake_preview(*_args, **_kwargs):
        return [
            SimpleNamespace(path="src/app.py", state="active_owned"),
            SimpleNamespace(path=".ai/cockpit/current_status.md", state="active_owned"),
        ]

    def fake_render_active_status(*_args, **kwargs):
        captured["ownership_counts"] = kwargs["ownership_counts"]
        return "status"

    monkeypatch.setattr(ai_generate_status, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_generate_status, "BACKTRACK_REPORT", tmp_path / "backtrack.json")
    monkeypatch.setattr(ai_generate_status, "ownership_preview", fake_preview)
    monkeypatch.setattr(ai_generate_status, "render_active_status", fake_render_active_status)
    monkeypatch.setattr(
        ai_generate_status,
        "create_observability",
        lambda **_kwargs: type("Obs", (), {"status_generated": lambda *_args, **_kwargs: None})(),
    )

    ai_generate_status.write_active_status(
        contract, summary, output=output, observability_log=tmp_path / "events.jsonl"
    )

    assert captured["ownership_counts"]["active_owned"] == 1


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
    monkeypatch.setattr(
        __import__("sys"), "argv", ["ai_generate_status.py", str(broken), "--output", str(output)]
    )
    assert ai_generate_status.main() == 1


def test_status_consistency_rejects_live_no_active_changes(tmp_path, monkeypatch):
    status = tmp_path / "status.md"
    status.write_text(
        "\n".join(
            [
                "# AI Cockpit Current Status",
                "",
                "- State: `no_active_work_item`",
                "",
                "## Changed Files",
                "",
                "- none",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_status_consistency, "active_contracts", lambda: [])
    monkeypatch.setattr(ai_check_status_consistency, "active_summaries", lambda: [])

    def fake_run(command, **_kwargs):
        if command[:3] == ["git", "rev-parse", "--verify"]:
            return type("Result", (), {"returncode": 0, "stdout": "head\n"})()
        if command[:3] == ["git", "diff", "--name-only"]:
            return type("Result", (), {"returncode": 0, "stdout": "src/app.py\n"})()
        if command[:3] == ["git", "ls-files", "--others"]:
            return type("Result", (), {"returncode": 0, "stdout": ""})()
        return type("Result", (), {"returncode": 0, "stdout": ""})()

    monkeypatch.setattr(ai_check_status_consistency.subprocess, "run", fake_run)

    issues = ai_check_status_consistency.validate_status_consistency(status)

    assert (
        "cockpit status no-active state must not persist changed files; run `make repair-ai-status`"
        in issues
    )


def test_no_active_status_excludes_repository_changes(tmp_path, monkeypatch):
    output = tmp_path / "status.md"
    monkeypatch.setattr(
        ai_generate_status,
        "changed_paths",
        lambda: [".ai/cockpit/current_status.md", "src/app.py", "tests/test_app.py"],
    )
    monkeypatch.setattr(
        ai_generate_status, "project_relative", lambda _path: ".ai/cockpit/current_status.md"
    )

    ai_generate_status.write_no_active_status(output)

    text = output.read_text(encoding="utf-8")
    assert "`src/app.py`" not in text
    assert "`.ai/cockpit/current_status.md`" not in text
    assert "Worktree Changes: `present`" in text
    assert "Worktree Change Count: `2`" in text
    assert "Ownership Preview: `ambiguous`" in text
    assert "intentionally excludes transient worktree changes" in text
    assert "check-ai-pr" in text
