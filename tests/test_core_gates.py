import json
import sys

import ai_check_review_policy
import ai_check_status
import ai_check_status_consistency


class ObservabilityStub:
    def check_passed(self, **kwargs):
        return None

    def check_failed(self, **kwargs):
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
