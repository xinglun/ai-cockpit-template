import json
from pathlib import Path

import ai_check_pr
import pytest


def write_pair(root, name, scope, changed, *, approved=False):
    archive = root / ".ai" / "work-items" / "archive" / "2026"
    archive.mkdir(parents=True, exist_ok=True)
    contract_path = archive / f"{name}.contract.json"
    summary_path = archive / f"{name}.summary.json"
    contract = {
        "contractVersion": 2,
        "workItemId": name,
        "mode": "code",
        "title": name,
        "baseCommit": "a" * 40,
        "baselineDirtyPaths": [],
        "scope": scope,
        "outOfScope": [],
        "sources": ["spec"],
        "unknowns": [],
        "notCodable": False,
        "acceptance": ["done"],
        "verification": [{"check": "projectTest", "required": False}],
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
        "restrictedWriteApproval": {
            "approved": approved,
            "approvedBy": "reviewer",
            "reason": "fixture",
        }
        if approved
        else {"approved": False},
        "rollbackNote": "revert",
    }
    summary = {
        "summaryVersion": 2,
        "workItemId": name,
        "contractPath": contract_path.relative_to(root).as_posix(),
        "changedFiles": [{"path": path, "reason": "covered"} for path in changed],
        "sourcesUsed": ["spec"],
        "verification": [{"check": "projectTest", "result": "not_run"}],
        "unknownsRemaining": [],
        "risk": {"level": "low", "detail": "none"},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
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


def fake_git_result(stdout="", returncode=0, stderr=""):
    return type(
        "Result",
        (),
        {"returncode": returncode, "stdout": stdout, "stderr": stderr},
    )()


def test_aggregate_pr_covers_earlier_and_later_work_items(tmp_path, monkeypatch):
    first = write_pair(tmp_path, "first", ["src/first.py"], ["src/first.py"])
    second = write_pair(tmp_path, "second", ["src/second.py"], ["src/second.py"])
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    patch_changes(
        monkeypatch,
        [
            "src/first.py",
            "src/second.py",
            first.relative_to(tmp_path).as_posix(),
            str(first.relative_to(tmp_path)).replace(".contract", ".summary"),
            second.relative_to(tmp_path).as_posix(),
            str(second.relative_to(tmp_path)).replace(".contract", ".summary"),
        ],
    )

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


def test_aggregate_pr_prefers_latest_effective_owner(tmp_path, monkeypatch):
    first = write_pair(tmp_path, "first", ["src/shared.py"], ["src/shared.py"])
    second = write_pair(tmp_path, "second", ["src/shared.py"], ["src/shared.py"])
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    patch_changes(monkeypatch, ["src/shared.py"])

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [first, second])
    assert issues == []


def test_aggregate_pr_prefers_input_order_over_rank(tmp_path, monkeypatch):
    first = write_pair(
        tmp_path, "z_unapproved", [".github/workflows/ci.yml"], [".github/workflows/ci.yml"]
    )
    second = write_pair(
        tmp_path,
        "a_approved",
        [".github/workflows/ci.yml"],
        [".github/workflows/ci.yml"],
        approved=True,
    )
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    monkeypatch.setattr(
        ai_check_pr,
        "archive_pair_rank",
        lambda contract_path, summary_path: {
            first: (
                20,
                first.relative_to(tmp_path).as_posix(),
                first.relative_to(tmp_path).as_posix().replace(".contract", ".summary"),
            ),
            second: (
                10,
                second.relative_to(tmp_path).as_posix(),
                second.relative_to(tmp_path).as_posix().replace(".contract", ".summary"),
            ),
        }[contract_path],
    )
    patch_changes(
        monkeypatch,
        [
            ".github/workflows/ci.yml",
            first.relative_to(tmp_path).as_posix(),
            first.relative_to(tmp_path).as_posix().replace(".contract", ".summary"),
            second.relative_to(tmp_path).as_posix(),
            second.relative_to(tmp_path).as_posix().replace(".contract", ".summary"),
        ],
    )

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [first, second])
    assert not any("restricted path lacks approval" in issue for issue in issues)


def test_aggregate_pr_rejects_when_unapproved_archive_is_last_in_order(tmp_path, monkeypatch):
    first = write_pair(
        tmp_path,
        "a_approved",
        [".github/workflows/ci.yml"],
        [".github/workflows/ci.yml"],
        approved=True,
    )
    second = write_pair(
        tmp_path, "z_unapproved", [".github/workflows/ci.yml"], [".github/workflows/ci.yml"]
    )
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    monkeypatch.setattr(
        ai_check_pr,
        "archive_pair_rank",
        lambda contract_path, summary_path: {
            first: (
                10,
                first.relative_to(tmp_path).as_posix(),
                first.relative_to(tmp_path).as_posix().replace(".contract", ".summary"),
            ),
            second: (
                20,
                second.relative_to(tmp_path).as_posix(),
                second.relative_to(tmp_path).as_posix().replace(".contract", ".summary"),
            ),
        }[contract_path],
    )
    patch_changes(
        monkeypatch,
        [
            ".github/workflows/ci.yml",
            first.relative_to(tmp_path).as_posix(),
            first.relative_to(tmp_path).as_posix().replace(".contract", ".summary"),
            second.relative_to(tmp_path).as_posix(),
            second.relative_to(tmp_path).as_posix().replace(".contract", ".summary"),
        ],
    )

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [first, second])
    assert any("restricted path lacks approval" in issue for issue in issues)


def test_aggregate_pr_preserves_discovery_order_for_default_archive_paths(tmp_path, monkeypatch):
    first = write_pair(tmp_path, "first", ["src/first.py"], ["src/first.py"])
    second = write_pair(tmp_path, "second", ["src/second.py"], ["src/second.py"])
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    monkeypatch.setattr(
        ai_check_pr,
        "run_git",
        lambda args: type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": "\n".join(
                    [
                        f"A\t{second.relative_to(tmp_path).as_posix()}",
                        f"A\t{second.relative_to(tmp_path).as_posix().replace('.contract', '.summary')}",
                        f"A\t{first.relative_to(tmp_path).as_posix()}",
                        f"A\t{first.relative_to(tmp_path).as_posix().replace('.contract', '.summary')}",
                    ]
                )
                + "\n",
                "stderr": "",
            },
        )(),
    )
    monkeypatch.setattr(
        ai_check_pr, "changed_paths", lambda *args, **kwargs: ["src/second.py", "src/first.py"]
    )

    assert ai_check_pr.archived_contract_paths("a" * 40) == [second, first]


@pytest.mark.parametrize(
    ("worktree_hash", "parent_hash", "expected"),
    [
        ("dirty-worktree", "parent-blob", False),
        ("shared-blob", "shared-blob", True),
    ],
)
def test_no_op_restore_uses_current_worktree_not_head(
    tmp_path, monkeypatch, worktree_hash, parent_hash, expected
):
    base = "a" * 40
    path = ".ai/work-items/archive/2026/example.summary.json"
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)

    calls = []

    def fake_run_git(args):
        calls.append(tuple(args))
        if args == ["hash-object", "--no-filters", path]:
            return fake_git_result(stdout=f"{worktree_hash}\n")
        if args == ["rev-parse", f"{base}^:{path}"]:
            return fake_git_result(stdout=f"{parent_hash}\n")
        if args == ["rev-parse", f"HEAD:{path}"]:
            raise AssertionError("no-op restore check must not consult HEAD")
        return fake_git_result(stdout="\n")

    monkeypatch.setattr(ai_check_pr, "run_git", fake_run_git)

    assert ai_check_pr._is_no_op_restore(base, path) is expected
    assert ["hash-object", "--no-filters", path] in [list(call) for call in calls]


def test_pr_bundle_does_not_exempt_dirty_archive_restore_from_ownership(tmp_path, monkeypatch):
    new = write_pair(tmp_path, "new", ["src/new.py"], ["src/new.py"])
    new_contract = new.relative_to(tmp_path).as_posix()
    new_summary = new_contract.replace(".contract", ".summary")
    restored_summary = ".ai/work-items/archive/2026/restored.summary.json"
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)

    def fake_run_git(args):
        if args == ["diff", "--name-status", "-z", "a" * 40 + "...HEAD"]:
            return fake_git_result(
                stdout="\0".join([f"A\t{new_contract}", f"A\t{new_summary}"]) + "\0"
            )
        if args == ["hash-object", "--no-filters", restored_summary]:
            return fake_git_result(stdout="dirty-worktree\n")
        if args == ["rev-parse", f"{'a' * 40}^:{restored_summary}"]:
            return fake_git_result(stdout="parent-blob\n")
        return fake_git_result(stdout="\n")

    monkeypatch.setattr(ai_check_pr, "run_git", fake_run_git)
    patch_changes(
        monkeypatch,
        [new_contract, new_summary, restored_summary],
        statuses={restored_summary: "M"},
    )

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [new])

    assert any(
        "complete PR diff path lacks paired ownership" in issue and restored_summary in issue
        for issue in issues
    )
    assert not any(
        "archive PR policy is append-only" in issue and restored_summary in issue
        for issue in issues
    )


def test_pr_bundle_still_exempts_clean_archive_restore_from_ownership(tmp_path, monkeypatch):
    new = write_pair(tmp_path, "new", ["src/new.py"], ["src/new.py"])
    new_contract = new.relative_to(tmp_path).as_posix()
    new_summary = new_contract.replace(".contract", ".summary")
    restored_summary = ".ai/work-items/archive/2026/restored.summary.json"
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)

    def fake_run_git(args):
        if args == ["diff", "--name-status", "-z", "a" * 40 + "...HEAD"]:
            return fake_git_result(
                stdout="\0".join([f"A\t{new_contract}", f"A\t{new_summary}"]) + "\0"
            )
        if args == ["hash-object", "--no-filters", restored_summary]:
            return fake_git_result(stdout="shared-blob\n")
        if args == ["rev-parse", f"{'a' * 40}^:{restored_summary}"]:
            return fake_git_result(stdout="shared-blob\n")
        return fake_git_result(stdout="\n")

    monkeypatch.setattr(ai_check_pr, "run_git", fake_run_git)
    patch_changes(
        monkeypatch,
        [new_contract, new_summary, restored_summary],
        statuses={restored_summary: "M"},
    )

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [new])

    assert not any(
        "complete PR diff path lacks paired ownership" in issue and restored_summary in issue
        for issue in issues
    )


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

    assert any(
        "archive PR policy is append-only" in issue and old_summary in issue for issue in issues
    )


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


def test_pr_rejects_archive_restoration_even_when_it_looks_like_a_restore(tmp_path, monkeypatch):
    new = write_pair(tmp_path, "new", ["src/new.py"], ["src/new.py"])
    new_contract = new.relative_to(tmp_path).as_posix()
    new_summary = new_contract.replace(".contract", ".summary")
    old = write_pair(tmp_path, "old", ["src/old.py"], ["src/old.py"])
    old_summary = old.relative_to(tmp_path).as_posix().replace(".contract", ".summary")
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    paths = ["src/new.py", new_contract, new_summary, old_summary]
    patch_changes(monkeypatch, paths, statuses={old_summary: "M"})

    issues = ai_check_pr.validate_pr_bundle("a" * 40, [new])

    assert any(
        "archive PR policy is append-only" in issue and old_summary in issue for issue in issues
    )


def test_pr_keeps_non_archive_modified_paths_valid(tmp_path, monkeypatch):
    pair = write_pair(tmp_path, "task", ["src/shared.py"], ["src/shared.py"])
    policy = tmp_path / "scope.yaml"
    policy.write_text("allowAlways:\n", encoding="utf-8")
    monkeypatch.setattr(ai_check_pr, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ai_check_pr, "SCOPE_POLICY", policy)
    changed = pair.relative_to(tmp_path).as_posix()
    patch_changes(
        monkeypatch,
        ["src/shared.py", changed, changed.replace(".contract", ".summary")],
        statuses={"src/shared.py": "M"},
    )

    assert ai_check_pr.validate_pr_bundle("a" * 40, [pair]) == []
