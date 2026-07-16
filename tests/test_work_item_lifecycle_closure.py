from __future__ import annotations

import inspect

import pytest

import ai_close_work_item as closure


def test_archived_evidence_uses_strict_summary_validation() -> None:
    source = inspect.getsource(closure._verify_archived_evidence)
    assert "legacy_archive=False" in source


class FakeGit:
    def __init__(
        self,
        *,
        fail_on: tuple[str, ...] | None = None,
        remote_branch_exists: bool = False,
        remote_check_returncode: int | None = None,
    ) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.fail_on = fail_on
        self.remote_branch_exists = remote_branch_exists
        self.remote_check_returncode = remote_check_returncode
        self.current_branch = "codex/example"
        self.base_worktree_path = ""

    def __call__(self, args: list[str] | tuple[str, ...], check: bool) -> closure.CommandResult:
        command = tuple(args)
        self.commands.append(command)
        normalized = command[2:] if command[:1] == ("-C",) else command
        if self.fail_on and normalized[: len(self.fail_on)] == self.fail_on:
            if check:
                raise RuntimeError(f"forced failure: {' '.join(normalized)}")
            return closure.CommandResult(1, "", "forced failure")
        if normalized == ("branch", "--show-current"):
            branch = "main" if command[:1] == ("-C",) else self.current_branch
            return closure.CommandResult(0, f"{branch}\n")
        if normalized == ("switch", "main"):
            self.current_branch = "main"
            return closure.CommandResult(0, "")
        if normalized == ("switch", "--detach", "HEAD"):
            self.current_branch = ""
            return closure.CommandResult(0, "")
        if normalized == ("worktree", "list", "--porcelain"):
            if self.base_worktree_path:
                return closure.CommandResult(
                    0,
                    "worktree /tmp/base-worktree\nHEAD abc123\nbranch refs/heads/main\n\n",
                )
            return closure.CommandResult(0, "")
        if normalized == ("status", "--porcelain", "--untracked-files=all"):
            return closure.CommandResult(0, "")
        if normalized[:2] == ("rev-parse", "main") or normalized[:2] == (
            "rev-parse",
            "origin/main",
        ):
            return closure.CommandResult(0, "abc123\n")
        if normalized[:3] == ("ls-remote", "--exit-code", "--heads"):
            if self.remote_check_returncode is not None:
                return closure.CommandResult(
                    self.remote_check_returncode, "", "remote check failed"
                )
            return closure.CommandResult(0 if self.remote_branch_exists else 2, "", "")
        return closure.CommandResult(0, "")


def prepare(monkeypatch: pytest.MonkeyPatch, fake: FakeGit) -> None:
    monkeypatch.setattr(
        closure,
        "_verify_archived_evidence",
        lambda _task: closure.PROJECT_ROOT / ".ai/work-items/archive/2026/example.contract.json",
    )
    monkeypatch.setattr(closure, "_discover_base", lambda _runner: ("origin", "main"))
    monkeypatch.setattr(
        closure,
        "_verify_pr",
        lambda _runner, _branch, _base: {"url": "https://example.test/pr/1"},
    )


def test_success_orders_synchronization_before_branch_deletion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGit()
    prepare(monkeypatch, fake)

    result = closure.close_work_item("example", fake)

    assert result["state"] == "closed"
    assert fake.commands.index(("switch", "main")) < fake.commands.index(
        ("branch", "-D", "codex/example")
    )
    assert fake.commands.index(("branch", "-D", "codex/example")) < fake.commands.index(
        ("push", "origin", "--delete", "codex/example")
    )


def test_unmerged_pr_blocks_all_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGit()
    prepare(monkeypatch, fake)
    monkeypatch.setattr(
        closure,
        "_verify_pr",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("pull request is not merged")),
    )

    with pytest.raises(RuntimeError, match="not merged"):
        closure.close_work_item("example", fake)

    assert ("switch", "main") not in fake.commands
    assert not any(command[:2] == ("branch", "-D") for command in fake.commands)
    assert not any(command[:3] == ("push", "origin", "--delete") for command in fake.commands)


def test_base_branch_error_explains_that_closure_must_identify_work_item_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGit()
    fake.current_branch = "main"
    prepare(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="still-identifiable Work Item branch"):
        closure.close_work_item("example", fake)

    assert fake.commands == [("branch", "--show-current")]


def test_base_branch_worktree_occupancy_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGit()
    fake.base_worktree_path = "/tmp/base-worktree"
    prepare(monkeypatch, fake)

    result = closure.close_work_item("example", fake)

    assert ("worktree", "list", "--porcelain") in fake.commands
    assert result["state"] == "closed"
    assert ("-C", "/tmp/base-worktree", "merge", "--ff-only", "origin/main") in fake.commands


def test_incomplete_archived_evidence_blocks_before_branch_inspection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGit()
    monkeypatch.setattr(
        closure,
        "_verify_archived_evidence",
        lambda _task: (_ for _ in ()).throw(RuntimeError("archived Work Item evidence is invalid")),
    )

    with pytest.raises(RuntimeError, match="evidence is invalid"):
        closure.close_work_item("example", fake)

    assert fake.commands == []


def test_branch_mapping_mismatch_blocks_before_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGit()
    prepare(monkeypatch, fake)
    monkeypatch.setattr(
        closure,
        "_verify_pr",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("head branch does not match")),
    )

    with pytest.raises(RuntimeError, match="head branch"):
        closure.close_work_item("example", fake)

    assert ("switch", "main") not in fake.commands


def test_dirty_worktree_blocks_before_pr_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGit()
    prepare(monkeypatch, fake)
    monkeypatch.setattr(
        closure,
        "_require_clean_worktree",
        lambda _runner: (_ for _ in ()).throw(RuntimeError("worktree or index is not clean")),
    )

    with pytest.raises(RuntimeError, match="not clean"):
        closure.close_work_item("example", fake)

    assert ("switch", "main") not in fake.commands


def test_non_fast_forward_blocks_before_branch_deletion(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGit(fail_on=("merge", "--ff-only"))
    prepare(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="forced failure"):
        closure.close_work_item("example", fake)

    assert not any(command[:2] == ("branch", "-D") for command in fake.commands)
    assert not any(command[:3] == ("push", "origin", "--delete") for command in fake.commands)


def test_remote_deletion_failure_does_not_report_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGit(
        fail_on=("push", "origin", "--delete"),
        remote_branch_exists=True,
    )
    prepare(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="remote work branch still exists"):
        closure.close_work_item("example", fake)

    assert ("branch", "-D", "codex/example") in fake.commands
    assert fake.commands.index(("switch", "main")) < fake.commands.index(
        ("branch", "-D", "codex/example")
    )


def test_remote_deletion_race_is_accepted_when_postcondition_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGit(fail_on=("push", "origin", "--delete"))
    prepare(monkeypatch, fake)

    result = closure.close_work_item("example", fake)

    assert result["state"] == "closed"
    assert ("fetch", "origin", "--prune") in fake.commands
    assert fake.commands[-1] == ("rev-parse", "origin/main")


def test_remote_deletion_failure_with_unverifiable_state_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGit(
        fail_on=("push", "origin", "--delete"),
        remote_check_returncode=1,
    )
    prepare(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="could not verify remote work branch deletion"):
        closure.close_work_item("example", fake)
