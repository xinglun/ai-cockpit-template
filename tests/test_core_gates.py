import json
import sys
from types import SimpleNamespace

import pytest

import ai_check_review_policy
import ai_common
import ai_check_scope
import ai_check_status
import ai_check_status_consistency
import ai_checkpoint
import ai_finish
import ai_generate_status
import ai_governance_compression


def test_governance_entrypoints_can_clean_ambient_git_environment():
    assert all(not key.startswith("GIT_") for key in ai_common.clean_git_environment())


@pytest.fixture(autouse=True)
def isolate_diff_ownership_preview(monkeypatch):
    monkeypatch.setattr(ai_finish, "preview", lambda **_kwargs: [])
    monkeypatch.setattr(ai_finish, "ensure_work_item_branch", lambda: None)


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
    assert ai_check_review_policy.review_focus(
        {"reviewReadiness": {"expectedReviewFocus": ["CI", ""]}}
    ) == ["CI"]


def test_status_check_main_accepts_matching_ready_status(tmp_path, monkeypatch):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    status = tmp_path / "status.md"
    contract.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "mode": "code",
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
                "verification": [{"check": "quality", "result": "passed"}],
                "reviewReadiness": {
                    "status": "ready",
                    "reason": "fixture",
                    "expectedReviewFocus": [],
                },
                "unknownsRemaining": [],
                "risk": {"level": "low", "detail": "fixture"},
                "guidelinesCompliance": [],
                "checkpointEvidence": [],
                "residualRisks": [],
            }
        ),
        encoding="utf-8",
    )
    model = ai_governance_compression.derive_governance_status(
        json.loads(contract.read_text(encoding="utf-8")),
        json.loads(summary.read_text(encoding="utf-8")),
    )
    status.write_text(
        ai_governance_compression.render_active_status(
            model,
            work_item_id="task",
            mode="code",
            contract_path=str(contract),
            summary_path=str(summary),
            generated_at="<timestamp>",
            ownership_counts={},
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        ai_check_status, "create_observability", lambda **kwargs: ObservabilityStub()
    )
    monkeypatch.setattr(ai_check_status, "BACKTRACK_REPORT", tmp_path / "backtrack.json")
    monkeypatch.setattr(ai_check_status, "ownership_preview", lambda **_kwargs: [])
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_check_status.py", str(status), "--contract", str(contract), "--summary", str(summary)],
    )

    assert ai_check_status.main() == 0
    assert ai_check_status.required_commands(json.loads(contract.read_text(encoding="utf-8"))) == [
        "quality"
    ]


def test_status_check_main_accepts_generated_status_with_unresolved_ownership(
    tmp_path, monkeypatch
):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    status = tmp_path / "status.md"
    contract.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "mode": "code",
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
                "verification": [{"check": "quality", "result": "passed"}],
                "reviewReadiness": {
                    "status": "ready",
                    "reason": "fixture",
                    "expectedReviewFocus": [],
                },
                "unknownsRemaining": [],
                "risk": {"level": "low", "detail": "fixture"},
                "guidelinesCompliance": [],
                "checkpointEvidence": [],
                "residualRisks": [],
            }
        ),
        encoding="utf-8",
    )
    unresolved_preview = [
        SimpleNamespace(path="src/app.py", state="unowned"),
    ]

    monkeypatch.setattr(ai_generate_status, "PROJECT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        ai_generate_status, "ownership_preview", lambda **_kwargs: unresolved_preview
    )
    monkeypatch.setattr(ai_check_status, "ownership_preview", lambda **_kwargs: unresolved_preview)
    monkeypatch.setattr(
        ai_generate_status,
        "create_observability",
        lambda **_kwargs: type("Obs", (), {"status_generated": lambda *_args, **_kwargs: None})(),
    )
    monkeypatch.setattr(
        ai_check_status,
        "create_observability",
        lambda **_kwargs: ObservabilityStub(),
    )

    ai_generate_status.write_active_status(
        contract, summary, output=status, observability_log=tmp_path / "events.jsonl"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_check_status.py",
            "status.md",
            "--contract",
            "task.contract.json",
            "--summary",
            "task.summary.json",
        ],
    )

    assert ai_check_status.main() == 0
    text = status.read_text(encoding="utf-8")
    assert "Recommendation: `needs_investigation`" in text
    assert "diff ownership unresolved: 1" in text


def test_status_consistency_covers_empty_paired_and_unpaired_states(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    status = tmp_path / "current_status.md"
    monkeypatch.setattr(ai_check_status_consistency, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_status_consistency, "ACTIVE_DIR", active)

    status.write_text("- State: `no_active_work_item`\n", encoding="utf-8")
    assert ai_check_status_consistency.validate_status_consistency(status) == []
    assert ai_check_status_consistency.live_no_active_changed_files(status) == []

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


def test_status_consistency_rejects_live_no_active_changes(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    status = tmp_path / "current_status.md"
    status.write_text(
        "- State: `no_active_work_item`\n\n## Changed Files\n\n- none\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_status_consistency, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_status_consistency, "ACTIVE_DIR", active)

    def fake_run(command, **kwargs):
        if command[:3] == ["git", "rev-parse", "--verify"]:
            return SimpleNamespace(returncode=0, stdout="head\n")
        if command[:3] == ["git", "diff", "--name-only"]:
            return SimpleNamespace(returncode=0, stdout="src/app.py\n")
        if command[:3] == ["git", "ls-files", "--others"]:
            return SimpleNamespace(returncode=0, stdout="")
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(ai_check_status_consistency.subprocess, "run", fake_run)

    issues = ai_check_status_consistency.validate_status_consistency(status)

    assert (
        "cockpit status no-active state must not persist changed files; run `make repair-ai-status`"
        in issues
    )


def test_status_consistency_ignores_uncommitted_archive_evidence(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    status = tmp_path / "current_status.md"
    status.write_text(
        "- State: `no_active_work_item`\n\n## Changed Files\n\n- none\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_status_consistency, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_status_consistency, "ACTIVE_DIR", active)

    def fake_run(command, **kwargs):
        if command[:3] == ["git", "rev-parse", "--verify"]:
            return SimpleNamespace(returncode=0, stdout="head\n")
        if command[:3] == ["git", "diff", "--name-only"]:
            return SimpleNamespace(
                returncode=0,
                stdout=".ai/work-items/archive/2026/task.summary.json\n",
            )
        if command[:3] == ["git", "ls-files", "--others"]:
            return SimpleNamespace(returncode=0, stdout="")
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(ai_check_status_consistency.subprocess, "run", fake_run)

    assert ai_check_status_consistency.validate_status_consistency(status) == []


def test_checkpoint_main_reports_required_state(tmp_path, monkeypatch, capsys):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "mode": "code",
                "notCodable": False,
                "executionDecision": {"status": "continue"},
                "scope": ["src/**"],
                "outOfScope": [],
                "unknowns": [],
                "acceptance": ["done"],
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(
        json.dumps(
            {
                "verification": [{"check": "quality", "result": "passed"}],
                "reviewReadiness": {"expectedReviewFocus": ["quality"]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_checkpoint.py",
            "--contract",
            str(contract),
            "--summary",
            str(summary),
            "--stage",
            "before_finish",
        ],
    )

    assert ai_checkpoint.main() == 0
    output = capsys.readouterr().out
    assert "Required Checks Passed: `1`" in output
    assert "problem: not provided" in output
    assert "constraint: not provided" in output
    assert "rationale: not provided" in output
    assert "Ready for final status generation" in output


def test_finish_evidence_redacts_and_replaces_existing_result(tmp_path, monkeypatch):
    summary = tmp_path / "task.summary.json"
    summary.write_text(
        json.dumps(
            {
                "verification": [{"check": "quality", "result": "not_run"}],
            }
        ),
        encoding="utf-8",
    )
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
        worktree_digest="c" * 64,
    )
    ai_finish.record_result(summary, item)

    recorded = json.loads(summary.read_text(encoding="utf-8"))["verification"]
    assert recorded == [item]
    assert "secret-value" not in item["outputSummary"]
    assert "<LOCAL_PATH>" in item["outputSummary"]
    truncated_private_key = "".join(["-" * 5, "BEGIN PRIVATE KEY", "-" * 5, "\n", "A" * 40])
    truncated_item = ai_finish.evidence(
        "quality",
        "make quality",
        0,
        12,
        f"prefix {truncated_private_key}",
        contract_hash="a" * 64,
        commit_sha="b" * 40,
        execution_contract_path=".ai/work-items/active/task.contract.json",
        execution_summary_path=".ai/work-items/active/task.summary.json",
        worktree_digest="c" * 64,
    )
    assert "[PRIVATE_KEY_REDACTED]" in truncated_item["outputSummary"]
    assert "BEGIN PRIVATE KEY" not in truncated_item["outputSummary"]
    for key_kind in ("RSA" + " PRIVATE KEY", "OPENSSH" + " PRIVATE KEY"):
        fragment = "".join(["-" * 5, "BEGIN ", key_kind, "-" * 5, "\n", key_kind, "-body-fragment"])
        fragment_item = ai_finish.evidence(
            "quality",
            "make quality",
            0,
            12,
            f"prefix {fragment}",
            contract_hash="a" * 64,
            commit_sha="b" * 40,
            execution_contract_path=".ai/work-items/active/task.contract.json",
            execution_summary_path=".ai/work-items/active/task.summary.json",
            worktree_digest="c" * 64,
        )
        assert fragment_item["outputSummary"] == "prefix [PRIVATE_KEY_REDACTED]"
        assert f"{key_kind}-body-fragment" not in fragment_item["outputSummary"]
    long_private_key = "".join(
        [
            "-" * 5,
            "BEGIN PRIVATE KEY",
            "-" * 5,
            "\n",
            "A" * 800,
            "\n",
            "-" * 5,
            "END PRIVATE KEY",
            "-" * 5,
        ]
    )
    long_item = ai_finish.evidence(
        "quality",
        "make quality",
        0,
        12,
        f"prefix {long_private_key} suffix",
        contract_hash="a" * 64,
        commit_sha="b" * 40,
        execution_contract_path=".ai/work-items/active/task.contract.json",
        execution_summary_path=".ai/work-items/active/task.summary.json",
        worktree_digest="c" * 64,
    )
    assert "[PRIVATE_KEY_REDACTED]" in long_item["outputSummary"]
    assert "BEGIN PRIVATE KEY" not in long_item["outputSummary"]
    assert (
        ai_finish.pending_evidence(
            "quality",
            "make quality",
            contract_hash="a" * 64,
            commit_sha="b" * 40,
            execution_contract_path="contract.json",
            execution_summary_path="summary.json",
            worktree_digest="c" * 64,
        )["runner"]
        == "ai_finish_pending"
    )


def test_finish_record_result_requires_active_summary(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    summary = active / "task.summary.json"
    archived_summary = archive / summary.name
    archived_summary.write_text(
        json.dumps({"verification": [{"check": "quality", "result": "not_run"}]}), encoding="utf-8"
    )
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)

    item = ai_finish.evidence(
        "quality",
        "make quality",
        0,
        1,
        "passed",
        contract_hash="a" * 64,
        commit_sha="b" * 40,
        execution_contract_path=".ai/work-items/active/task.contract.json",
        execution_summary_path=".ai/work-items/active/task.summary.json",
        worktree_digest="c" * 64,
    )
    with pytest.raises(FileNotFoundError, match="summary not found"):
        ai_finish.record_result(summary, item)

    recorded = json.loads(archived_summary.read_text(encoding="utf-8"))["verification"]
    assert recorded == [{"check": "quality", "result": "not_run"}]
    assert not summary.exists()


def test_finish_main_fails_when_contract_is_missing(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "missing"])

    assert ai_finish.main() == 1


def test_finish_refuses_repository_base_branch_before_running_checks(tmp_path, monkeypatch, capsys):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    (active / "task.contract.json").write_text(
        json.dumps({"contractVersion": 2, "workItemId": "task", "verification": []}),
        encoding="utf-8",
    )
    (active / "task.summary.json").write_text(json.dumps({"verification": []}), encoding="utf-8")

    def reject_base_branch():
        raise RuntimeError(
            "ai-finish must run on the dedicated Work Item branch; current branch is the repository base branch"
        )

    monkeypatch.setattr(ai_finish, "ensure_work_item_branch", reject_base_branch)
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task"])

    assert ai_finish.main() == 2
    assert "dedicated Work Item branch" in capsys.readouterr().err


def test_finish_branch_guard_compares_current_branch_with_discovered_base(monkeypatch):
    monkeypatch.setattr(ai_finish, "repository_base_branch", lambda: "main")

    with pytest.raises(RuntimeError, match="repository base branch"):
        ai_finish.validate_work_item_branch("main", "main")


def test_finish_branch_discovery_handles_remote_head_and_no_remote_head(monkeypatch):
    def one_remote(args):
        if args == ["remote"]:
            return SimpleNamespace(returncode=0, stdout="origin\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="origin/main\n", stderr="")

    monkeypatch.setattr(ai_finish, "run_git", one_remote)

    assert ai_finish.repository_base_branch() == "main"

    monkeypatch.setattr(
        ai_finish,
        "run_git",
        lambda args: SimpleNamespace(
            returncode=0,
            stdout="" if args == ["remote"] else "",
            stderr="",
        ),
    )
    assert ai_finish.repository_base_branch() is None


@pytest.mark.parametrize("branches", [("main", "trunk"), ("main", "main")])
def test_finish_branch_discovery_rejects_ambiguous_remote_heads(monkeypatch, branches):
    def two_remotes(args):
        if args == ["remote"]:
            return SimpleNamespace(returncode=0, stdout="origin\nupstream\n", stderr="")
        remote = args[-1].split("/")[2]
        branch = branches[0] if remote == "origin" else branches[1]
        return SimpleNamespace(returncode=0, stdout=f"{remote}/{branch}\n", stderr="")

    monkeypatch.setattr(ai_finish, "run_git", two_remotes)

    with pytest.raises(RuntimeError, match="multiple remote HEAD targets"):
        ai_finish.repository_base_branch()


def test_finish_branch_helpers_fail_closed_for_git_errors_and_detached_head(monkeypatch):
    monkeypatch.setattr(
        ai_finish,
        "run_git",
        lambda _args: SimpleNamespace(returncode=1, stdout="", stderr="bad git"),
    )
    with pytest.raises(RuntimeError, match="cannot enumerate Git remotes"):
        ai_finish.repository_base_branch()


def test_finish_allows_branch_when_no_remote_head_is_configured(monkeypatch):
    monkeypatch.setattr(ai_finish, "repository_base_branch", lambda: None)
    monkeypatch.setattr(ai_finish, "_git_output", lambda _args: "codex/task")

    ai_finish.ensure_work_item_branch()


def test_finish_main_records_required_check_failure(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_finish, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(
        ai_finish,
        "render_check_command",
        lambda *_args, **_kwargs: ("make quality", ["make", "quality"]),
    )
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
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
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
    monkeypatch.setattr(
        ai_finish, "run", lambda command: executed.append(command) or (0, 2, "passed")
    )
    monkeypatch.setattr(ai_finish, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task", "--no-archive"])

    assert ai_finish.main() == 0
    assert len(executed) == 10
    assert executed[0] == ["make", "quality"]
    assert executed[-1][:2] == ["make", "check-ai-change-summary"]
    recorded = json.loads(summary.read_text(encoding="utf-8"))["verification"]
    assert all(item["result"] == "passed" for item in recorded)
    assert {item["check"] for item in recorded} >= {"quality", "aiStatus", "aiSummary"}


def test_finish_main_demotes_readiness_when_final_status_check_fails(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
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

    def fail_final_status(command):
        executed.append(command)
        is_final_status = len(executed) > 6 and command[:2] == ["make", "check-ai-status"]
        return (1, 2, "status failed") if is_final_status else (0, 2, "passed")

    monkeypatch.setattr(ai_finish, "run", fail_final_status)
    monkeypatch.setattr(ai_finish, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task", "--no-archive"])

    assert ai_finish.main() == 1
    readiness = json.loads(summary.read_text(encoding="utf-8"))["reviewReadiness"]
    assert readiness["status"] == "not_ready"


def test_finish_main_fails_when_summary_is_missing(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    contract.write_text(
        json.dumps({"contractVersion": 2, "workItemId": "task", "verification": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task"])

    assert ai_finish.main() == 1


def test_finish_main_rejects_invalid_verification_list(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps({"contractVersion": 2, "workItemId": "task", "verification": "bad"}),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task"])

    assert ai_finish.main() == 1


def test_finish_main_rejects_skip_quality_for_required_check(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(
        sys, "argv", ["ai_finish.py", "--task", "task", "--skip-quality", "--no-archive"]
    )

    assert ai_finish.main() == 2


def test_finish_main_reports_unknown_check_id(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [{"check": "missingCheck", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_finish, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(
        ai_finish,
        "render_check_command",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("unknown check")),
    )
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task", "--no-archive"])

    assert ai_finish.main() == 2


def test_finish_main_fails_when_archive_step_fails(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_finish, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(
        ai_finish,
        "render_check_command",
        lambda check, **_kwargs: (f"make {check}", ["make", check]),
    )

    def run(command):
        if command[:2] == ["make", "archive-work-item"]:
            return 5, 3, "archive failed"
        return 0, 1, "passed"

    monkeypatch.setattr(ai_finish, "run", run)
    monkeypatch.setattr(ai_finish, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task"])

    assert ai_finish.main() == 5


def test_finish_main_fails_when_stabilization_check_fails(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_finish, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(
        ai_finish,
        "render_check_command",
        lambda check, **_kwargs: (f"make {check}", ["make", check]),
    )

    def run(command):
        if command[:2] == ["make", "check-ai-status"]:
            return 4, 2, "status failed"
        return 0, 1, "passed"

    monkeypatch.setattr(ai_finish, "run", run)
    monkeypatch.setattr(ai_finish, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task", "--no-archive"])

    assert ai_finish.main() == 4


def test_finish_main_allows_optional_check_failure(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [
                    {"check": "quality", "required": True},
                    {"check": "aiReviewPolicy", "required": False},
                ],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_finish, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(
        ai_finish,
        "render_check_command",
        lambda check, **_kwargs: (f"make {check}", ["make", check]),
    )

    def run(command):
        if command[-1] == "aiReviewPolicy":
            return 1, 1, "optional failed"
        return 0, 1, "passed"

    monkeypatch.setattr(ai_finish, "run", run)
    monkeypatch.setattr(ai_finish, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task", "--no-archive"])

    assert ai_finish.main() == 0
    recorded = json.loads(summary.read_text(encoding="utf-8"))["verification"]
    optional = next(item for item in recorded if item["check"] == "aiReviewPolicy")
    assert optional["result"] == "failed"


def test_finish_main_rejects_contract_version_one(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps({"contractVersion": 1, "workItemId": "task", "verification": []}),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task", "--no-archive"])

    assert ai_finish.main() == 2


def test_finish_main_rejects_inline_command_verification(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [{"command": "make evil", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task", "--no-archive"])

    assert ai_finish.main() == 2


def test_finish_main_archives_on_success(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(
        json.dumps(
            {
                "contractVersion": 2,
                "workItemId": "task",
                "verification": [{"check": "quality", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"verification": []}), encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_finish, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_finish, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(
        ai_finish,
        "render_check_command",
        lambda check, **_kwargs: (f"make {check}", ["make", check]),
    )
    monkeypatch.setattr(ai_finish, "run", lambda command: (0, 1, "passed"))
    monkeypatch.setattr(ai_finish, "create_observability", lambda **_kwargs: ObservabilityStub())
    monkeypatch.setattr(sys, "argv", ["ai_finish.py", "--task", "task"])

    assert ai_finish.main() == 0


def test_finish_run_executes_command_and_prints_output(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    code, duration, output = ai_finish.run(["printf", "passed"])
    assert code == 0
    assert "passed" in output
    assert duration >= 0
    assert "passed" in capsys.readouterr().out


def test_finish_record_result_replaces_non_list_verification(tmp_path, monkeypatch):
    summary = tmp_path / "task.summary.json"
    summary.write_text('{"verification": "bad"}\n', encoding="utf-8")
    monkeypatch.setattr(ai_finish, "PROJECT_ROOT", tmp_path)
    item = {"check": "quality", "result": "passed"}
    ai_finish.record_result(summary, item)
    recorded = json.loads(summary.read_text(encoding="utf-8"))["verification"]
    assert recorded == [item]


def test_scope_main_reports_out_of_scope_and_dependency_failures(tmp_path, monkeypatch, capsys):
    contract = tmp_path / "task.contract.json"
    contract.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "scope": ["src/**"],
                "outOfScope": ["src/private/**"],
                "destructiveChangePolicy": {"allowed": False},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        ai_check_scope, "changed_paths", lambda _contract: ["src/private/key.py", "README.md"]
    )
    monkeypatch.setattr(
        ai_check_scope,
        "simple_yaml_lists",
        lambda _path: {"dependencyScopeRules.src/**": ["tests/**"]},
    )
    monkeypatch.setattr(
        ai_check_scope, "create_observability", lambda **_kwargs: ObservabilityStub()
    )
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
    summary.write_text(
        json.dumps({"workItemId": "task", "reviewReadiness": {"expectedReviewFocus": []}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_review_policy, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_review_policy, "POLICY", policy)
    monkeypatch.setattr(ai_check_review_policy, "REPORT", tmp_path / "target" / "review.json")
    monkeypatch.setattr(ai_check_review_policy, "changed_paths", lambda: [".ai/guards/scope.yaml"])
    monkeypatch.setattr(
        ai_check_review_policy, "create_observability", lambda **_kwargs: ObservabilityStub()
    )
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

    def fake_run(_command, **_kwargs):
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text("- State: `no_active_work_item`\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(ai_check_status_consistency.subprocess, "run", fake_run)
    assert ai_check_status_consistency.repair_status(status) == 0


def test_status_consistency_rejects_no_active_changed_files(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    status = tmp_path / "current_status.md"
    status.write_text(
        "- State: `no_active_work_item`\n\n## Changed Files\n\n- `src/old.py`\n\n## Next Action\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_check_status_consistency, "ACTIVE_DIR", active)
    issues = ai_check_status_consistency.validate_status_consistency(status)
    assert any("must not persist changed files" in issue for issue in issues)
