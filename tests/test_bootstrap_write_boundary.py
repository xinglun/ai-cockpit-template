from pathlib import Path

import pytest

from bootstrap_write_boundary import BoundaryError, build_plan, execute_plan


def test_dry_run_and_unconfirmed_execution_do_not_write(tmp_path: Path):
    plan = build_plan(tmp_path, {".ai/config.yaml": "version: 1\n"}, {".ai/config.yaml"})

    dry_result = execute_plan(plan, dry_run=True, confirmed=True, confirmation_value="CONFIRM")
    assert dry_result.written == ()
    assert dry_result.planned == (".ai/config.yaml",)
    assert not (tmp_path / ".ai/config.yaml").exists()

    pending_result = execute_plan(plan, confirmed=False)
    assert pending_result.written == ()
    assert not (tmp_path / ".ai/config.yaml").exists()


def test_non_interactive_execution_requires_exact_confirmation(tmp_path: Path):
    plan = build_plan(tmp_path, {".ai/config.yaml": "version: 1\n"}, {".ai/config.yaml"})

    with pytest.raises(BoundaryError, match="confirmation"):
        execute_plan(plan, confirmed=True, non_interactive=True, confirmation_value="yes")


def test_paths_must_be_allowed_and_cannot_escape_or_follow_symlinks(tmp_path: Path):
    with pytest.raises(BoundaryError, match="allowlist"):
        build_plan(tmp_path, {"README.md": "changed\n"}, {".ai/config.yaml"})
    with pytest.raises(BoundaryError, match="path"):
        build_plan(tmp_path, {"../outside": "changed\n"}, {"../outside"})

    outside = tmp_path.parent / "outside.txt"
    outside.write_text("keep\n", encoding="utf-8")
    link = tmp_path / ".ai-link"
    link.symlink_to(outside)
    with pytest.raises(BoundaryError, match="symlink"):
        build_plan(tmp_path, {".ai-link": "overwrite\n"}, {".ai-link"})


def test_managed_makefile_block_is_idempotent_and_preserves_project_content(tmp_path: Path):
    makefile = tmp_path / "Makefile"
    makefile.write_text("project-target:\n\t@echo project\n\n", encoding="utf-8")
    block = "ai-cockpit-quality:\n\t@echo quality\n"
    first = build_plan(tmp_path, {"Makefile": block}, {"Makefile"}, managed_makefile_block=block)
    execute_plan(first, confirmed=True, confirmation_value="CONFIRM")
    original = makefile.read_text(encoding="utf-8")
    assert "project-target:" in original
    assert original.count("AI_COCKPIT_MANAGED_BEGIN") == 1

    second = build_plan(tmp_path, {"Makefile": block}, {"Makefile"}, managed_makefile_block=block)
    execute_plan(second, confirmed=True, confirmation_value="CONFIRM")
    assert makefile.read_text(encoding="utf-8") == original


def test_malformed_managed_makefile_markers_fail_closed(tmp_path: Path):
    (tmp_path / "Makefile").write_text("# AI_COCKPIT_MANAGED_BEGIN\n", encoding="utf-8")
    with pytest.raises(BoundaryError, match="marker"):
        build_plan(
            tmp_path,
            {"Makefile": "ai-cockpit-quality:\n"},
            {"Makefile"},
            managed_makefile_block="ai-cockpit-quality:\n",
        )


def test_confirmed_execution_rechecks_repository_before_writing(tmp_path: Path):
    plan = build_plan(tmp_path, {".ai/config.yaml": "version: 1\n"}, {".ai/config.yaml"})
    with pytest.raises(BoundaryError, match="drift"):
        execute_plan(
            plan,
            confirmed=True,
            confirmation_value="CONFIRM",
            drift_check=lambda: {
                "ok": False,
                "mismatches": {"commit": {"expected": "a", "actual": "b"}},
            },
        )
    assert not (tmp_path / ".ai/config.yaml").exists()
