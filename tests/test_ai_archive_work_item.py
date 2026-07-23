import json
from argparse import Namespace

import ai_archive_work_item


def test_archive_growth_requires_projected_same_work_item_reservation():
    contract = {"workItemId": "task"}
    issues = ai_archive_work_item.validate_archive_growth_reservation(
        contract, 487, {"max": {"archiveGrowth": 488}}
    )
    assert any("reservation is required" in issue for issue in issues)


def test_archive_growth_reservation_accepts_projected_count_and_repayment():
    contract = {
        "workItemId": "task",
        "budgetImpact": {
            "expectedMetrics": {"archiveGrowth": 488},
            "approved": True,
            "repaymentWorkItem": "task",
            "repaymentRecords": [".ai/guards/governance_complexity_policy.yaml"],
        },
    }
    assert (
        ai_archive_work_item.validate_archive_growth_reservation(
            contract, 487, {"max": {"archiveGrowth": 488}}
        )
        == []
    )


def test_archive_growth_accepts_bounded_future_reservation():
    contract = {
        "workItemId": "budget-window",
        "budgetImpact": {
            "expectedMetrics": {"archiveGrowth": 496},
            "reservedFutureMetrics": {"archiveGrowth": 497},
            "approved": True,
            "repaymentWorkItem": "budget-window",
            "repaymentRecords": ["policy"],
        },
    }
    assert (
        ai_archive_work_item.validate_archive_growth_reservation(
            contract, 495, {"max": {"archiveGrowth": 497}}
        )
        == []
    )


def test_archive_growth_string_policy_limit_rejects_unapproved_overrun():
    contract = {
        "workItemId": "task",
        "budgetImpact": {"expectedMetrics": {"archiveGrowth": 493}},
    }
    issues = ai_archive_work_item.validate_archive_growth_reservation(
        contract, 492, {"max": {"archiveGrowth": "492"}}
    )
    assert any(
        "projected archiveGrowth=493 exceeds configured maximum 492" in issue for issue in issues
    )
    assert any("requires budgetImpact.approved=true" in issue for issue in issues)


def test_archive_growth_reservation_rejects_stale_projection():
    contract = {
        "workItemId": "task",
        "budgetImpact": {"expectedMetrics": {"archiveGrowth": 487}},
    }
    issues = ai_archive_work_item.validate_archive_growth_reservation(
        contract, 487, {"max": {"archiveGrowth": 488}}
    )
    assert any("reservation is stale" in issue for issue in issues)


def test_archive_moves_task_owned_success_criteria_sibling(tmp_path):
    contract = tmp_path / ".ai" / "work-items" / "active" / "task.contract.json"
    assert ai_archive_work_item.owned_success_criteria_path(contract) == contract.with_name(
        "task.success.json"
    )


def test_next_archive_sequence_prefers_existing_index(tmp_path, monkeypatch):
    archive = tmp_path / "archive"
    archive.mkdir()
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive)
    (archive / "index.json").write_text(
        '{"indexVersion": 1, "entries": [{"archiveSequence": 41}]}',
        encoding="utf-8",
    )

    assert ai_archive_work_item._next_archive_sequence() == 42


def test_archive_manifest_is_stable_and_excludes_generated_status(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    contract.write_text(json.dumps({"workItemId": "task", "baseCommit": "base"}), encoding="utf-8")
    summary.write_text(
        json.dumps({"workItemId": "task", "contractPath": "task.contract.json"}), encoding="utf-8"
    )

    manifest = ai_archive_work_item._archive_manifest(
        contract_target=contract, summary_target=summary, archive_sequence=7
    )

    assert manifest["manifestVersion"] == 1
    assert manifest["archiveSequence"] == 7
    assert manifest["generatedStatusExcluded"] is True
    assert "manifestSha256" not in manifest
    assert (
        manifest["contractSha256"]
        == __import__("hashlib").sha256(contract.read_bytes()).hexdigest()
    )
    assert (
        manifest["summarySha256"] == __import__("hashlib").sha256(summary.read_bytes()).hexdigest()
    )


def test_current_worktree_digest_excludes_self_referential_summary(monkeypatch):
    monkeypatch.setattr(
        ai_archive_work_item,
        "changed_paths",
        lambda _contract: ["src/app.py", ".ai/work-items/active/task.summary.json"],
    )
    monkeypatch.setattr(ai_archive_work_item, "path_fingerprint", lambda path: f"digest:{path}")

    digest = ai_archive_work_item._current_worktree_digest(
        {"summaryPath": ".ai/work-items/active/task.summary.json"}
    )

    assert digest == ai_archive_work_item._worktree_digest(["src/app.py"])


def test_archive_entry_references_manifest_digest(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    target = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    target.mkdir(parents=True)
    contract_path = target / "task.contract.json"
    summary_path = target / "task.summary.json"
    manifest_path = target / "task.archive-manifest.json"
    contract_path.write_text(json.dumps({"workItemId": "task"}), encoding="utf-8")
    summary_path.write_text(json.dumps({"workItemId": "task"}), encoding="utf-8")
    manifest_path.write_text(
        json.dumps({"format": "ai-cockpit-archive-manifest"}), encoding="utf-8"
    )

    entry = ai_archive_work_item._archive_entry(
        contract_path=contract_path,
        summary_path=summary_path,
        target_dir=target,
        archive_sequence=1,
    )

    assert entry["manifestPath"].endswith("task.archive-manifest.json")
    assert len(entry["manifestSha256"]) == 64


def test_is_ignored_matches_gitignore_archive_patterns(tmp_path, monkeypatch):
    (tmp_path / ".gitignore").write_text("local/*.json\n!local/kept.json\n", encoding="utf-8")
    local = tmp_path / "local"
    local.mkdir()
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)

    assert ai_archive_work_item._is_ignored(local / "old.json")
    assert not ai_archive_work_item._is_ignored(local / "kept.json")
    assert not ai_archive_work_item._is_ignored(tmp_path / "other.txt")


def test_restore_files_moves_archive_inputs_back(tmp_path):
    active = tmp_path / ".ai" / "work-items" / "active"
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    active.mkdir(parents=True)
    archive.mkdir(parents=True)

    contract = active / "task.contract.json"
    summary = active / "task.summary.json"
    archived_contract = archive / contract.name
    archived_summary = archive / summary.name
    archived_contract.write_text("contract", encoding="utf-8")
    archived_summary.write_text("summary", encoding="utf-8")

    ai_archive_work_item._restore_files(
        [(contract, archived_contract), (summary, archived_summary)]
    )

    assert contract.read_text(encoding="utf-8") == "contract"
    assert summary.read_text(encoding="utf-8") == "summary"
    assert not archived_contract.exists()
    assert not archived_summary.exists()


def test_load_archive_index_adds_unindexed_authoritative_pair(tmp_path, monkeypatch):
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    contract = archive / "legacy.contract.json"
    summary = archive / "legacy.summary.json"
    contract.write_text(json.dumps({"workItemId": "legacy"}), encoding="utf-8")
    summary.write_text(
        json.dumps(
            {
                "workItemId": "legacy",
                "contractPath": ".ai/work-items/archive/2026/legacy.contract.json",
            }
        ),
        encoding="utf-8",
    )
    (archive.parent / "index.json").write_text('{"entries": []}', encoding="utf-8")
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive.parent)

    result = ai_archive_work_item._load_archive_index()

    assert len(result["entries"]) == 1
    assert result["entries"][0]["contractPath"].endswith("legacy.contract.json")


def test_load_archive_index_deduplicates_pair_and_prefers_strict_entry(tmp_path, monkeypatch):
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    (archive / "task.contract.json").write_text("{}", encoding="utf-8")
    (archive / "task.summary.json").write_text("{}", encoding="utf-8")
    index = archive.parent / "index.json"
    pair = {
        "contractPath": ".ai/work-items/archive/2026/task.contract.json",
        "summaryPath": ".ai/work-items/archive/2026/task.summary.json",
    }
    index.write_text(
        json.dumps(
            {
                "entries": [
                    {**pair, "workItemId": "task", "archivedAt": "legacy"},
                    {
                        **pair,
                        "workItemId": "task",
                        "contractSha256": "a" * 64,
                        "summarySha256": "b" * 64,
                        "archivedAt": "current",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive.parent)

    result = ai_archive_work_item._load_archive_index()

    assert len(result["entries"]) == 1
    assert result["entries"][0]["archivedAt"] == "current"


def test_load_archive_index_drops_stale_pair(tmp_path, monkeypatch):
    archive = tmp_path / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True)
    (archive.parent / "index.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "contractPath": ".ai/work-items/archive/2026/removed.contract.json",
                        "summaryPath": ".ai/work-items/archive/2026/removed.summary.json",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive.parent)

    result = ai_archive_work_item._load_archive_index()

    assert result["entries"] == []


def test_main_dry_run_validates_summary_and_current_digest(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    active = project_root / ".ai" / "work-items" / "active"
    archive = project_root / ".ai" / "work-items" / "archive" / "2026"
    active.mkdir(parents=True)
    archive.mkdir(parents=True)

    contract_path = active / "task.contract.json"
    summary_path = active / "task.summary.json"
    contract_path.write_text(
        json.dumps(
            {
                "workItemId": "task",
                "mode": "code",
                "scope": ["src/app.py"],
                "budgetImpact": {
                    "expectedMetrics": {"archiveGrowth": 1},
                    "approved": True,
                    "repaymentWorkItem": "task",
                    "repaymentRecords": ["policy"],
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ai_archive_work_item, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(ai_archive_work_item, "ACTIVE_DIR", active)
    monkeypatch.setattr(
        ai_archive_work_item, "ARCHIVE_BASE_DIR", project_root / ".ai" / "work-items" / "archive"
    )
    monkeypatch.setattr(ai_archive_work_item, "validate_contract", lambda _contract: [])
    monkeypatch.setattr(ai_archive_work_item, "validate_summary", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        ai_archive_work_item, "changed_paths", lambda _contract: ["src/app.py", "src/app.py"]
    )
    monkeypatch.setattr(ai_archive_work_item, "path_fingerprint", lambda path: f"digest:{path}")

    current_digest = ai_archive_work_item._current_worktree_digest({"scope": ["src/app.py"]})

    class DummyObservability:
        def record(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(
        ai_archive_work_item, "create_observability", lambda *_args, **_kwargs: DummyObservability()
    )
    monkeypatch.setattr(
        ai_archive_work_item,
        "parse_args",
        lambda: Namespace(contract=str(contract_path), dry_run=True),
    )
    summary_path.write_text(
        json.dumps(
            {
                "verification": [
                    {"check": "aiSummary", "result": "passed", "worktreeDigest": current_digest}
                ]
            }
        ),
        encoding="utf-8",
    )

    assert ai_archive_work_item.main() == 0
    assert contract_path.exists()
    assert summary_path.exists()
