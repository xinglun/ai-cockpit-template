import json
import sys
from types import SimpleNamespace

import ai_check_review_policy
import ai_check_scope
import ai_check_status
import ai_check_status_consistency
import ai_checkpoint
import ai_finish


class ObservabilityStub:
    def check_started(self, **kwargs):
        return None

    def check_passed(self, **kwargs):
        return None

    def check_failed(self, **kwargs):
        return None

    def guard_violation(self, **kwargs):
        return None

    def work_item_finished(self, **kwargs):
        return None


def test_review_policy_helpers_parse_focus_and_paths(tmp_path, monkeypatch):
    policy = tmp_path / "review.yaml"
    policy.write_text(
        "requiredReviewChecklist:\n  include:\n    - .ai/**\n  exclude:\n    - .ai/work-items/archive/**\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_review_policy, "POLICY", policy)

    include, exclude = ai_check_review_policy.review_patterns()
    assert ai_check_review_policy.detect(
        [".ai/guards/scope.yaml", ".ai/work-items/archive/task.json", "src/app.py"],
        include=include,
        exclude=exclude,
    ) == [".ai/guards/scope.yaml"]
    assert ai_check_review_policy.review_focus(None) == []
    assert ai_check_review_policy.review_focus({"reviewReadiness": {"expectedReviewFocus": ["CI", ""]}}) == ["CI"]


def test_status_check_main_accepts_matching_ready_status(tmp_path, monkeypatch):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    status = tmp_path / "status.md"
    contract.write_text(json.dumps({
        "workItemId": "task",
        "mode": "code",
        "verification": [{"check": "aiWorkItem", "required": True}],
    }), encoding="utf-8")
    summary.write_text(json.dumps({
        "verification": [{"check": "aiWorkItem", "result": "passed"}],
    }), encoding="utf-8")
    status.write_text(
        "- Task: `task`\n- Mode: `code`\n"
        f"- Contract Path: `{contract}`\n- Summary Path: `{summary}`\n"
        "- State: `ready_for_review`\n## Blocking\n- none\n"
        "## Required Checks\n- `aiWorkItem`: passed\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_status, "create_observability", lambda **kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_check_status.py", str(status), "--contract", str(contract), "--summary", str(summary)])

    assert ai_check_status.main() == 0
    assert ai_check_status.required_commands(json.loads(contract.read_text(encoding="utf-8"))) == ["aiWorkItem"]


def test_status_consistency_covers_empty_paired_and_unpaired_states(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    status = tmp_path / "current_status.md"
    monkeypatch.setattr(ai_check_status_consistency, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_status_consistency, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_check_status_consistency, "repository_changes_for_status", lambda _path: [])

    status.write_text("- State: `no_active_work_item`\n", encoding="utf-8")
    assert ai_check_status_consistency.validate_status_consistency(status) == []

    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text("{}\n", encoding="utf-8")
    issues = ai_check_status_consistency.validate_status_consistency(status)
    assert any("no matching Summary" in issue for issue in issues)

    summary.write_text("{}\n", encoding="utf-8")
    status.write_text(
        "- State: `in_progress`\n- Task: `task`\n"
        "- Contract Path: `.ai/work-items/active/task.contract.json`\n"
        "- Summary Path: `.ai/work-items/active/task.summary.json`\n",
        encoding="utf-8",
    )
    assert ai_check_status_consistency.validate_status_consistency(status) == []


def test_checkpoint_main_reports_required_state(tmp_path, monkeypatch, capsys):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    contract.write_text(json.dumps({
        "workItemId": "task",
        "mode": "code",
        "notCodable": False,
        "executionDecision": {"status": "continue"},
        "scope": ["src/**"],
        "outOfScope": [],
        "unknowns": [],
        "acceptance": ["done"],
        "verification": [{"check": "quality", "required": True}],
    }), encoding="utf-8")
    summary.write_text(json.dumps({
        "verification": [{"check": "quality", "result": "passed"}],
        "reviewReadiness": {"expectedReviewFocus": ["quality"]},
    }), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_checkpoint.py", "--contract", str(contract), "--summary", str(summary), "--stage", "before_finish"],
    )

    assert ai_checkpoint.main() == 0
    output = capsys.readouterr().out
    assert "Required Checks Passed: `1`" in output
    assert "Ready for final status generation" in output


def test_finish_evidence_redacts_and_replaces_existing_result(tmp_path, monkeypatch):
    summary = tmp_path / "task.summary.json"
    summary.write_text(json.dumps({
        "verification": [{"check": "quality", "result": "not_run"}],
    }), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    item = ai_finish.evidence(
        "quality",
        "make quality",
        0,
        12,
        "token=secret-value /Users/example/project passed",
        contract_hash="a" * 64,
        commit_sha="b" * 40,
        execution_contract_path=".ai/work-items/active/task.contract.json",
        execution_summary_path=".ai/work-items/active/task.summary.json",
    )
    ai_finish.record_result(summary, item)

    recorded = json.loads(summary.read_text(encoding="utf-8"))["verification"]
    assert recorded == [item]
    assert "secret-value" not in item["outputSummary"]
    assert "<LOCAL_PATH>" in item["outputSummary"]
    assert ai_finish.pending_evidence(
        "quality",
        "make quality",
        contract_hash="a" * 64,
        commit_sha="b" * 40,
        execution_contract_path="contract.json",
        execution_summary_path="summary.json",
    )["runner"] == "ai_finish_pending"


def test_finish_main_fails_when_contract_is_missing(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "missing"])

    assert ai_finish.main() == 1


def test_finish_main_records_required_check_failure(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(json.dumps({
        "contractVersion": 2,
        "workItemId": "task",
        "verification": [{"check": "quality", "required": True}],
    }), encoding="utf-8")
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_finish, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(ai_finish, "render_check_command", lambda *_args, **_kwargs: ("make quality", ["make", "quality"]))
    monkeypatch.setattr(ai_finish, "run", lambda _command: (3, 7, "quality failed"))
    monkeypatch.setattr(ai_finish, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task", "--no-archive"])

    assert ai_finish.main() == 3
    recorded = json.loads(summary.read_text(encoding="utf-8"))["verification"]
    assert recorded[0]["result"] == "failed"
    assert recorded[0]["exitCode"] == 3


def test_finish_main_stabilizes_successful_work_item(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(json.dumps({
        "contractVersion": 2,
        "workItemId": "task",
        "verification": [{"check": "quality", "required": True}],
    }), encoding="utf-8")
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_finish, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(
        ai_finish,
        "render_check_command",
        lambda check, **_kwargs: (f"make {check}", ["make", check]),
    )
    executed = []
    monkeypatch.setattr(ai_finish, "run", lambda command: (executed.append(command) or (0, 2, "passed")))
    monkeypatch.setattr(ai_finish, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task", "--no-archive"])

    assert ai_finish.main() == 0
    assert len(executed) == 6
    recorded = json.loads(summary.read_text(encoding="utf-8"))["verification"]
    assert all(item["result"] == "passed" for item in recorded)
    assert {item["check"] for item in recorded} >= {"quality", "aiStatus", "aiSummary"}


def test_scope_main_reports_out_of_scope_and_dependency_failures(tmp_path, monkeypatch, capsys):
    contract = tmp_path / "task.contract.json"
    contract.write_text(json.dumps({
        "workItemId": "task",
        "scope": ["src/**"],
        "outOfScope": ["src/private/**"],
        "destructiveChangePolicy": {"allowed": False},
    }), encoding="utf-8")
    monkeypatch.setattr(ai_check_scope, "changed_paths", lambda _contract: ["src/private/key.py", "README.md"])
    monkeypatch.setattr(
        ai_check_scope,
        "simple_yaml_lists",
        lambda _path: {"dependencyScopeRules.src/**": ["tests/**"]},
    )
    monkeypatch.setattr(ai_check_scope, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_check_scope.py", str(contract)])

    assert ai_check_scope.main() == 1
    errors = capsys.readouterr().err
    assert "matches outOfScope" in errors
    assert "dependency scope rule requires tests/**" in errors


def test_review_policy_main_writes_warning_report(tmp_path, monkeypatch):
    policy = tmp_path / ".ai" / "guards" / "ai_review_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text("requiredReviewChecklist:\n  include:\n    - .ai/**\n", encoding="utf-8")
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({"workItemId": "task", "reviewReadiness": {"expectedReviewFocus": []}}), encoding="utf-8")
    monkeypatch.setattr(ai_check_review_policy, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_review_policy, "POLICY", policy)
    monkeypatch.setattr(ai_check_review_policy, "REPORT", tmp_path / "target" / "review.json")
    monkeypatch.setattr(ai_check_review_policy, "changed_paths", lambda: [".ai/guards/scope.yaml"])
    monkeypatch.setattr(ai_check_review_policy, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_check_review_policy.py", "--summary", str(summary)])

    assert ai_check_review_policy.main() == 0
    report = json.loads(ai_check_review_policy.REPORT.read_text(encoding="utf-8"))
    assert report["status"] == "warning"
    assert report["matchedPaths"] == [".ai/guards/scope.yaml"]


def test_status_consistency_repair_no_active_state(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    status = tmp_path / ".ai" / "cockpit" / "current_status.md"
    monkeypatch.setattr(ai_check_status_consistency, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_status_consistency, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_check_status_consistency, "DEFAULT_STATUS", status)
    monkeypatch.setattr(ai_check_status_consistency, "repository_changes_for_status", lambda _path: [])

    def fake_run(_command, **_kwargs):
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text("- State: `no_active_work_item`\n", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ai_check_status_consistency.subprocess, "run", fake_run)
    assert ai_check_status_consistency.repair_status(status) == 0


def test_status_consistency_rejects_stale_no_active_changed_files(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    status = tmp_path / "current_status.md"
    status.write_text(
        "- State: `no_active_work_item`\n\n## Changed Files\n\n- `src/old.py`\n\n## Next Action\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_status_consistency, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_check_status_consistency, "repository_changes_for_status", lambda _path: ["src/new.py"])

    issues = ai_check_status_consistency.validate_status_consistency(status)
    assert any("Changed Files do not match current Git changes" in issue for issue in issues)
