import json
import sys
import subprocess
import fcntl
import ai_archive_work_item
import ai_start


def archive_contract(mode: str = "review") -> dict[str, object]:
    return {
        "contractVersion": 2,
        "workItemId": "task",
        "mode": mode,
        "title": "Task",
        "baseCommit": "a" * 40,
        "baselineDirtyPaths": [],
        "scope": [
            "scripts/ai_archive_work_item.py",
            "tests/test_start_and_archive.py",
            ".ai/cockpit/current_status.md",
            ".ai/work-items/archive/**",
        ],
        "outOfScope": ["Product source changes"],
        "sources": [{"path": "scripts/ai_archive_work_item.py", "reason": "fixture"}],
        "unknowns": [],
        "notCodable": False,
        "acceptance": ["done"],
        "verification": [{"check": "quality", "required": True}],
        "riskAssessment": {"level": "low", "riskTypes": [], "reason": "fixture"},
        "agentCapability": {
            "canImplement": True,
            "canVerify": True,
            "needsHumanDecision": False,
            "blockedReason": "",
        },
        "executionDecision": {"status": "continue", "reason": "fixture"},
        "checkpointPolicy": {
            "requiredBeforeFinish": False,
            "requiredStages": [],
            "reason": "fixture",
        },
        "destructiveChangePolicy": {
            "allowed": False,
            "requiresHumanApproval": True,
            "allowPatterns": [],
        },
        "rollbackNote": "revert",
    }


def archive_summary(*, verification_result: str = "passed") -> dict[str, object]:
    return {
        "summaryVersion": 2,
        "workItemId": "task",
        "contractPath": ".ai/work-items/active/task.contract.json",
        "changedFiles": [
            {"path": ".ai/work-items/active/task.contract.json", "reason": "contract"},
            {"path": ".ai/work-items/active/task.summary.json", "reason": "summary"},
            {"path": ".ai/work-items/active/task.review.json", "reason": "review"},
        ],
        "sourcesUsed": ["scripts/ai_archive_work_item.py"],
        "verification": [
            {"check": "quality", "result": verification_result},
            {
                "check": "aiSummary",
                "result": "passed",
                "worktreeDigest": "a" * 64,
            },
        ],
        "unknownsRemaining": [],
        "risk": {"level": "low", "detail": "fixture"},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
    }


def stub_active_status(monkeypatch):
    monkeypatch.setattr(ai_start, "write_active_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ai_start, "run_make", lambda *_args, **_kwargs: (0, ""))


def test_ai_start_refreshes_only_stale_no_active_status(monkeypatch):
    stale = (
        "cockpit status Changed Files do not match current Git changes; run `make repair-ai-status`"
    )
    no_active_stale = (
        "cockpit status no-active state must not persist changed files; run `make repair-ai-status`"
    )
    calls = []
    monkeypatch.setattr(ai_start, "write_no_active_status", lambda path: calls.append(path))
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])

    assert ai_start.refresh_stale_no_active_status([stale]) == []
    assert calls == [ai_start.DEFAULT_STATUS]
    assert ai_start.refresh_stale_no_active_status([no_active_stale]) == []
    assert calls == [ai_start.DEFAULT_STATUS, ai_start.DEFAULT_STATUS]
    assert ai_start.refresh_stale_no_active_status(["different lifecycle error"]) == [
        "different lifecycle error"
    ]


def test_ai_start_default_contains_agent_risk_gate(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(ai_start, "capture_dirty_baseline", lambda: [])
    stub_active_status(monkeypatch)
    monkeypatch.setattr(
        ai_start,
        "create_observability",
        lambda **_: type("Obs", (), {"work_item_started": lambda *a, **k: None})(),
    )
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "sample", "--mode", "code"])

    assert ai_start.main() == 0
    contract = json.loads((active / "sample.contract.json").read_text(encoding="utf-8"))
    checks = [item["check"] for item in contract["verification"]]
    assert "aiAgentRisk" in checks
    assert "aiCheckpoint" in checks
    assert "aiReviewPolicy" in checks
    assert "aiDiffOwnership" in checks
    assert contract["contractVersion"] == 2
    assert contract["notCodable"] is False
    assert contract["baseCommit"] == "a" * 40
    assert contract["checkpointPolicy"]["requiredStages"] == ["before_edit", "before_finish"]
    assert ".ai/cockpit/current_status.md" in contract["scope"]


def test_ai_start_requires_initial_commit(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "")
    stub_active_status(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "sample"])

    assert ai_start.main() == 1
    assert not (active / "sample.contract.json").exists()


def test_ai_start_refuses_when_an_active_work_item_already_exists(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    (active / "existing.contract.json").write_text(
        json.dumps({"workItemId": "existing"}), encoding="utf-8"
    )
    (active / "existing.summary.json").write_text(
        json.dumps({"workItemId": "existing"}), encoding="utf-8"
    )
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(ai_start, "capture_dirty_baseline", lambda: [])
    stub_active_status(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "sample"])

    assert ai_start.main() == 1
    assert not (active / "sample.contract.json").exists()
    assert not (active / "sample.summary.json").exists()


def test_ai_start_refuses_when_start_lock_is_held(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    lock_path = ai_start.start_lock_path()
    lock_handle = lock_path.open("a+", encoding="utf-8")
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(ai_start, "capture_dirty_baseline", lambda: [])
    stub_active_status(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "sample"])

    try:
        assert ai_start.main() == 1
        assert not (active / "sample.contract.json").exists()
        assert not (active / "sample.summary.json").exists()
    finally:
        lock_handle.close()
        lock_path.unlink(missing_ok=True)


def test_archive_refuses_to_overwrite_existing_audit_record(tmp_path, monkeypatch):
    active = tmp_path / "active"
    archive = tmp_path / "archive"
    active.mkdir()
    contract = active / "task.contract.json"
    contract.write_text(json.dumps(archive_contract("review")), encoding="utf-8")
    year_dir = archive / str(__import__("datetime").datetime.now().year)
    year_dir.mkdir(parents=True)
    (year_dir / contract.name).write_text("existing", encoding="utf-8")
    monkeypatch.setattr(ai_archive_work_item, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive)
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["ai_archive_work_item.py", str(contract)])

    assert ai_archive_work_item.main() == 1


def test_archive_dry_run_and_successful_review_item(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    archive = tmp_path / ".ai" / "work-items" / "archive"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    contract.write_text(json.dumps(archive_contract("review")), encoding="utf-8")
    monkeypatch.setattr(ai_archive_work_item, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive)
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["ai_archive_work_item.py", str(contract), "--dry-run"])
    assert ai_archive_work_item.main() == 0
    assert contract.exists()

    calls = []

    def fake_run(cmd, cwd=None, check=False):
        calls.append(cmd)
        return None

    observer = type("Obs", (), {"record": lambda *_args, **_kwargs: None})()
    monkeypatch.setattr(ai_archive_work_item, "create_observability", lambda **_kwargs: observer)
    monkeypatch.setattr(ai_archive_work_item.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["ai_archive_work_item.py", str(contract)])
    assert ai_archive_work_item.main() == 0
    assert not contract.exists()
    assert list(archive.glob("*/task.contract.json"))
    assert any(
        any(str(part).endswith("ai_generate_status.py") for part in cmd) and "--no-active" in cmd
        for cmd in calls
    )


def test_archive_code_item_rewrites_summary_paths(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    archive = tmp_path / ".ai" / "work-items" / "archive"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    review = active / "task.review.json"
    contract.write_text(json.dumps(archive_contract("code")), encoding="utf-8")
    summary.write_text(json.dumps(archive_summary()), encoding="utf-8")
    review.write_text(json.dumps({"workItemId": "task", "result": "ok"}), encoding="utf-8")
    monkeypatch.setattr(ai_archive_work_item, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive)
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_archive_work_item, "validate_contract", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ai_archive_work_item, "validate_summary", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        ai_archive_work_item,
        "create_observability",
        lambda **_kwargs: type("Obs", (), {"record": lambda *_args, **_kwargs: None})(),
    )
    monkeypatch.setattr(ai_archive_work_item.subprocess, "run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        ai_archive_work_item, "_current_worktree_digest", lambda _contract: "a" * 64
    )
    monkeypatch.setattr(sys, "argv", ["ai_archive_work_item.py", str(contract)])

    assert ai_archive_work_item.main() == 0
    archived_summary = next(archive.glob("*/task.summary.json"))
    data = json.loads(archived_summary.read_text(encoding="utf-8"))
    assert "/active/" not in data["contractPath"]
    assert all("/archive/" in item["path"] for item in data["changedFiles"])
    assert any(item["path"].endswith("task.review.json") for item in data["changedFiles"])


def test_archive_rolls_back_when_status_regeneration_fails(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    archive = tmp_path / ".ai" / "work-items" / "archive"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(json.dumps(archive_contract("code")), encoding="utf-8")
    summary.write_text(json.dumps(archive_summary()), encoding="utf-8")
    monkeypatch.setattr(ai_archive_work_item, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive)
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_archive_work_item, "validate_contract", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ai_archive_work_item, "validate_summary", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        ai_archive_work_item, "_current_worktree_digest", lambda _contract: "a" * 64
    )

    def fake_run(cmd, cwd=None, check=False):
        if any(str(part).endswith("ai_generate_status.py") for part in cmd):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)
        return None

    monkeypatch.setattr(ai_archive_work_item.subprocess, "run", fake_run)
    monkeypatch.setattr(
        ai_archive_work_item,
        "create_observability",
        lambda **_kwargs: type("Obs", (), {"record": lambda *_args, **_kwargs: None})(),
    )
    monkeypatch.setattr(sys, "argv", ["ai_archive_work_item.py", str(contract)])

    assert ai_archive_work_item.main() == 1
    assert contract.exists()
    assert summary.exists()
    assert not list(archive.glob("*/task.contract.json"))


def test_archive_rejects_invalid_summary_before_moving_files(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    archive = tmp_path / ".ai" / "work-items" / "archive"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(json.dumps(archive_contract("code")), encoding="utf-8")
    summary.write_text(json.dumps(archive_summary(verification_result="not_run")), encoding="utf-8")
    monkeypatch.setattr(ai_archive_work_item, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive)
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["ai_archive_work_item.py", str(contract)])

    assert ai_archive_work_item.main() == 1
    assert contract.exists()
    assert summary.exists()
    assert not list(archive.rglob("task.contract.json"))


def test_archive_rejects_stale_worktree_digest_before_moving_files(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    archive = tmp_path / ".ai" / "work-items" / "archive"
    active.mkdir(parents=True)
    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    contract.write_text(json.dumps(archive_contract("code")), encoding="utf-8")
    summary_data = archive_summary()
    summary_data["verification"] = [
        {"check": "quality", "result": "passed"},
        {"check": "aiSummary", "result": "passed", "worktreeDigest": "b" * 64},
    ]
    summary.write_text(json.dumps(summary_data), encoding="utf-8")
    monkeypatch.setattr(ai_archive_work_item, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive)
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ai_archive_work_item, "_current_worktree_digest", lambda _contract: "a" * 64
    )
    monkeypatch.setattr(sys, "argv", ["ai_archive_work_item.py", str(contract)])

    assert ai_archive_work_item.main() == 1
    assert contract.exists()
    assert summary.exists()
    assert not list(archive.rglob("task.contract.json"))


def test_ai_start_journeys(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(ai_start, "capture_dirty_baseline", lambda: [])
    stub_active_status(monkeypatch)
    monkeypatch.setattr(
        ai_start,
        "create_observability",
        lambda **_: type("Obs", (), {"work_item_started": lambda *a, **k: None})(),
    )

    # Test refactor journey
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_start.py", "--task", "refactor_task", "--mode", "code", "--journey", "refactor"],
    )
    assert ai_start.main() == 0
    contract = json.loads((active / "refactor_task.contract.json").read_text(encoding="utf-8"))
    summary = json.loads((active / "refactor_task.summary.json").read_text(encoding="utf-8"))
    assert "Zero functional changes allowed." in contract["guidelines"]
    assert "Adding new features" in contract["outOfScope"]
    assert contract["destructiveChangePolicy"]["allowed"] is False
    assert any(
        item["guideline"] == "Zero functional changes allowed."
        for item in summary["guidelinesCompliance"]
    )

    for path in active.glob("*.json"):
        path.unlink()

    # Test cleanup journey
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_start.py", "--task", "cleanup_task", "--mode", "code", "--journey", "cleanup"],
    )
    assert ai_start.main() == 0
    contract_c = json.loads((active / "cleanup_task.contract.json").read_text(encoding="utf-8"))
    assert contract_c["destructiveChangePolicy"]["allowed"] is False
    assert contract_c["destructiveChangePolicy"]["requiresHumanApproval"] is True


def test_ai_start_generates_active_status(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    generated = []
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(ai_start, "capture_dirty_baseline", lambda: [])
    monkeypatch.setattr(
        ai_start,
        "write_active_status",
        lambda contract, summary, **_kwargs: generated.append((contract, summary)),
    )
    monkeypatch.setattr(ai_start, "run_make", lambda *_args, **_kwargs: (0, ""))
    monkeypatch.setattr(
        ai_start,
        "create_observability",
        lambda **_: type("Obs", (), {"work_item_started": lambda *a, **k: None})(),
    )
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "status_task", "--mode", "code"])

    assert ai_start.main() == 0
    assert generated == [
        (active / "status_task.contract.json", active / "status_task.summary.json"),
        (active / "status_task.contract.json", active / "status_task.summary.json"),
    ]


def test_ai_start_rolls_back_pair_when_status_generation_fails(tmp_path, monkeypatch):
    active = tmp_path / ".ai" / "work-items" / "active"
    active.mkdir(parents=True)
    status = tmp_path / ".ai" / "cockpit" / "current_status.md"
    status.parent.mkdir(parents=True)
    status.write_text("previous status\n", encoding="utf-8")
    monkeypatch.setattr(ai_start, "ACTIVE_DIR", active)
    monkeypatch.setattr(ai_start, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_start, "validate_status_consistency", lambda: [])
    monkeypatch.setattr(ai_start, "current_head", lambda: "a" * 40)
    monkeypatch.setattr(ai_start, "capture_dirty_baseline", lambda: [])
    monkeypatch.setattr(
        ai_start,
        "write_active_status",
        lambda *_: (_ for _ in ()).throw(RuntimeError("status failed")),
    )
    monkeypatch.setattr(sys, "argv", ["ai_start.py", "--task", "status_task", "--mode", "code"])

    assert ai_start.main() == 1
    assert not list(active.glob("status_task.*.json"))
    assert status.read_text(encoding="utf-8") == "previous status\n"
