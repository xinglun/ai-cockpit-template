import json
from pathlib import Path

import ai_check_pr


def write_pair(root, name, scope, changed):
    archive = root / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True, exist_ok=True)
    contract_path = archive / f"{name}.contract.json"
    summary_path = archive / f"{name}.summary.json"
    contract = {
        "contractVersion": 2, "workItemId": name, "mode": "code", "title": name,
        "baseCommit": "a" * 40, "baselineDirtyPaths": [], "scope": scope, "outOfScope": [],
        "sources": ["spec"], "unknowns": [], "notCodable": False, "acceptance": ["done"],
        "verification": [{"check": "projectTest", "required": False}],
        "destructiveChangePolicy": {"allowed": False, "requiresHumanApproval": True, "allowPatterns": []},
        "rollbackNote": "revert",
    }
    summary = {
        "workItemId": name, "contractPath": contract_path.relative_to(root).as_posix(),
        "changedFiles": [{"path": path, "reason": "covered"} for path in changed],
        "sourcesUsed": ["spec"], "verification": [{"check": "projectTest", "result": "not_run"}],
        "unknownsRemaining": [], "risk": {"level": "low", "detail": "none"},
        "generatedFiles": [], "destructiveChanges": [], "observedIssues": [],
    }
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    return contract_path


def patch_changes(monkeypatch, paths, *, statuses=None):
    statuses = statuses or {}
    monkeypatch.setattr(ai_check_pr, "changed_paths", lambda *args, **kwargs: paths)
    monkeypatch.setattr(
        ai_check_pr,
        "changed_name_status",
        lambda *args, **kwargs: [
            (statuses.get(path, "A" if path.startswith(".ai/work-items/archive/") else "M"), path)
            for path in paths
        ],
    )


def test_aggregate_pr_covers_earlier_and_later_work_items(tmp_path, monkeypatch):
    first = write_pair(tmp_path, "first", ["src/first.py"], ["src/first.py"])
    second = write_pair(tmp_path, "second", ["src/second.py"], ["src/second.py"])
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    patch_changes(monkeypatch, [
        "src/first.py", "src/second.py",
        first.relative_to(tmp_path).as_posix(), str(first.relative_to(tmp_path)).replace(".contract", ".summary"),
        second.relative_to(tmp_path).as_posix(), str(second.relative_to(tmp_path)).replace(".contract", ".summary"),
    ])

    assert ai_check_pr.validate_pr_bundle("a" * 40, [first, second]) == []


def test_aggregate_pr_rejects_uncovered_earlier_path(tmp_path, monkeypatch):
    closing = write_pair(tmp_path, "closing", ["src/closing.py"], ["src/closing.py"])
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    patch_changes(monkeypatch, ["src/earlier.py", "src/closing.py"])

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [closing])
    assert (
        "complete PR diff path lacks paired ownership (same Contract scope and Summary changedFiles): src/earlier.py"
        in issues
    )


def test_aggregate_pr_rejects_cross_pair_scope_and_summary_claims(tmp_path, monkeypatch):
    first = write_pair(tmp_path, "first", ["src/a.py"], ["src/b.py"])
    second = write_pair(tmp_path, "second", ["src/b.py"], ["src/a.py"])
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    patch_changes(monkeypatch, ["src/a.py", "src/b.py"])

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [first, second])
    assert len([issue for issue in issues if "lacks paired ownership" in issue]) == 2


def test_aggregate_pr_rejects_contract_v1_downgrade(tmp_path, monkeypatch):
    legacy = write_pair(tmp_path, "legacy", ["src/a.py"], ["src/a.py"])
    contract = json.loads(legacy.read_text(encoding="utf-8"))
    contract["contractVersion"] = 1
    contract["verification"] = [{"command": "sh -c 'true'", "required": True}]
    legacy.write_text(json.dumps(contract), encoding="utf-8")
    summary_path = Path(str(legacy).replace(".contract.json", ".summary.json"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["verification"] = [{"command": "sh -c 'true'", "result": "passed"}]
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    patch_changes(monkeypatch, ["src/a.py"])

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [legacy])
    assert any("PR archive evidence requires contractVersion 2" in issue for issue in issues)


def test_pr_rejects_summary_only_tampering_even_when_new_work_item_claims_it(tmp_path, monkeypatch):
    old = write_pair(tmp_path, "old", ["src/old.py"], ["src/old.py"])
    old_summary = str(old.relative_to(tmp_path)).replace(".contract", ".summary")
    new = write_pair(tmp_path, "new", [".ai/work-items/archive/**"], [old_summary])
    new_summary = str(new.relative_to(tmp_path)).replace(".contract", ".summary")
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    paths = [old_summary, new.relative_to(tmp_path).as_posix(), new_summary]
    patch_changes(monkeypatch, paths, statuses={old_summary: "M"})

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [new])

    assert any("archive PR policy is append-only" in issue and old_summary in issue for issue in issues)


def test_pr_rejects_contract_only_archive_modification(tmp_path, monkeypatch):
    contract = write_pair(tmp_path, "old", ["src/old.py"], ["src/old.py"])
    contract_rel = contract.relative_to(tmp_path).as_posix()
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    patch_changes(monkeypatch, [contract_rel], statuses={contract_rel: "M"})

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [])

    assert any("archive PR policy is append-only" in issue for issue in issues)


def test_pr_rejects_archive_delete_and_rename(tmp_path, monkeypatch):
    old = write_pair(tmp_path, "old", ["src/old.py"], ["src/old.py"])
    old_contract = old.relative_to(tmp_path).as_posix()
    old_summary = old_contract.replace(".contract", ".summary")
    renamed = write_pair(tmp_path, "renamed", ["src/old.py"], ["src/old.py"])
    renamed_contract = renamed.relative_to(tmp_path).as_posix()
    renamed_summary = renamed_contract.replace(".contract", ".summary")
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    paths = [old_contract, old_summary, renamed_contract, renamed_summary]
    patch_changes(
        monkeypatch,
        paths,
        statuses={old_contract: "D", old_summary: "D"},
    )

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [])

    assert sum("archive PR policy is append-only" in issue for issue in issues) == 2
