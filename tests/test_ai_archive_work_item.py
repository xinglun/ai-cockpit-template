import json
from argparse import Namespace

import ai_archive_work_item


def test_next_archive_sequence_prefers_existing_index(tmp_path, monkeypatch):
    archive = tmp_path / "archive"
    archive.mkdir()
    monkeypatch.setattr(ai_archive_work_item, "ARCHIVE_BASE_DIR", archive)
    (archive / "index.json").write_text(
        '{"indexVersion": 1, "entries": [{"archiveSequence": 41}]}',
        encoding="utf-8",
    )

    assert ai_archive_work_item._next_archive_sequence() == 42


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
        '{"workItemId": "task", "mode": "code", "scope": ["src/app.py"]}',
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
