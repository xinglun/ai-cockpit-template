import json
import re
import subprocess
from pathlib import Path

import pytest

import install_ai_cockpit as installer_mod
from install_ai_cockpit import Installer


ROOT = Path(__file__).resolve().parents[1]


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def init_git_repo(path: Path, filename: str, content: str, message: str) -> str:
    run(path, "git", "init", "-q")
    run(path, "git", "config", "user.email", "test@example.invalid")
    run(path, "git", "config", "user.name", "Test")
    (path / filename).write_text(content, encoding="utf-8")
    run(path, "git", "add", filename)
    run(path, "git", "commit", "-qm", message)
    return run(path, "git", "rev-parse", "HEAD").stdout.strip()


def test_installed_distribution_contains_pr_and_approval_wiring(tmp_path):
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )

    assert installer.install() == 0
    assert (tmp_path / "scripts" / "ai_check_pr.py").is_file()
    assert (tmp_path / "scripts" / "ai_start_receipt.py").is_file()
    assert (tmp_path / ".ai" / "README.md").is_file()
    assert (tmp_path / "scripts" / "ai_doctor.py").is_file()
    assert (tmp_path / "scripts" / "ai_onboard.py").is_file()


def test_installer_source_context_ignores_candidate_metadata(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "release.json").write_text('{"releaseTag":"v0.5.30"}\n', encoding="utf-8")
    (source / "next-release.json").write_text(
        '{"releaseTag":"v0.5.31","published":false}\n', encoding="utf-8"
    )

    installer = Installer(
        source=source,
        target=target,
        stack="generic",
        force=False,
        dry_run=True,
        with_examples=False,
        update_makefile=False,
    )

    assert installer.source_context() == ("v0.5.30", "local source")


def test_installed_distribution_contains_adoption_files(tmp_path):
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert installer.install() == 0
    assert (tmp_path / "scripts" / "ai_check_adoption_ready.py").is_file()
    assert (tmp_path / ".ai" / "cockpit" / "README.ja.md").is_file()
    assert (tmp_path / ".ai" / "cockpit" / "adoption.ja.md").is_file()
    assert not (tmp_path / ".ai" / "cockpit" / "bandit_low_risk_baseline.json").exists()
    assert not (tmp_path / ".ai" / "cockpit" / "provenance.json").exists()
    assert not (tmp_path / ".ai" / "cockpit" / "release-digests.json").exists()
    assert not (tmp_path / ".ai" / "cockpit" / "sbom.json").exists()
    assert "<!-- AI_COCKPIT_SECTION -->" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    managed = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "\n---\n" not in managed
    assert "\n# Agent Operating Rules" not in managed
    assert not list((tmp_path / ".ai" / "work-items" / "active").glob("*.json"))
    assert not list((tmp_path / ".ai" / "work-items" / "archive").rglob("*.json"))
    assert "- State: `no_active_work_item`" in (
        tmp_path / ".ai" / "cockpit" / "current_status.md"
    ).read_text(encoding="utf-8")
    assert ".ai/work-items/active/*.contract.json" in (tmp_path / ".gitignore").read_text(
        encoding="utf-8"
    )
    assert ".ai/work-items/active/*.review.json" in (tmp_path / ".gitignore").read_text(
        encoding="utf-8"
    )
    assert ".ai/cockpit/upgrade-backups/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")
    makefile_ai = (tmp_path / "Makefile.ai").read_text(encoding="utf-8")
    assert "check-ai-pr:" in makefile_ai
    assert "ai-doctor:" in makefile_ai
    assert "check-ai-adoption-ready:" in makefile_ai
    assert "scripts/ai_check_pr.py" in makefile_ai
    assert "ai-close-work-item:" in makefile_ai
    assert (tmp_path / "scripts" / "ai_close_work_item.py").is_file()
    assert "scripts/ai_check_guards.py $(if $(CONTRACT),--contract $(CONTRACT))" in makefile_ai
    assert (tmp_path / ".ai" / "glossary.md").read_text(encoding="utf-8") == (
        ROOT / "templates" / "glossary.md"
    ).read_text(encoding="utf-8")
    assert (tmp_path / ".ai" / "glossary.md").read_text(encoding="utf-8") != (
        ROOT / ".ai" / "glossary.md"
    ).read_text(encoding="utf-8")

    result = subprocess.run(
        ["make", "-n", "check-ai-pr", "AI_BASE_COMMIT=abc123"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'scripts/ai_check_pr.py --base "abc123"' in result.stdout


def test_installed_cursor_rule_defaults_to_opt_in_apply(tmp_path):
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )

    assert installer.install() == 0
    rule = (tmp_path / ".cursor" / "rules" / "ai-cockpit.mdc").read_text(encoding="utf-8")
    assert "alwaysApply: false" in rule
    assert "Always Apply" in rule


def test_create_adoption_warns_on_dirty_worktree_and_tracked_hygiene(tmp_path, capsys):
    init_git_repo(tmp_path, "README.md", "# Project\n", "initial")
    (tmp_path / ".DS_Store").write_text("noise\n", encoding="utf-8")
    subprocess.run(["git", "add", "-f", ".DS_Store"], cwd=tmp_path, check=True)
    (tmp_path / "dirty.txt").write_text("pending\n", encoding="utf-8")

    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )

    assert installer.install() == 2
    error = capsys.readouterr().err
    assert "WARN: Git worktree is not clean" in error
    assert "WARN: Tracked files commonly ignored locally (.DS_Store" in error
    assert "ERROR: --create-adoption requires a clean Git worktree before installation." in error
    assert not (tmp_path / ".ai").exists()


def test_create_adoption_warnings_parse_nul_delimited_status_records(tmp_path, monkeypatch):
    calls = []

    def fake_run(command, *, cwd, text, capture_output, check, env):
        calls.append(command)
        if command[:3] == [
            "git",
            f"--git-dir={tmp_path / '.git'}",
            f"--work-tree={tmp_path}",
        ] and command[3:] == ["status", "--porcelain", "-z"]:
            return subprocess.CompletedProcess(
                command, 0, stdout=" M plain.txt\0 M dir/line1\nline2.txt\0", stderr=""
            )
        if command[:3] == [
            "git",
            f"--git-dir={tmp_path / '.git'}",
            f"--work-tree={tmp_path}",
        ] and command[3:] == ["ls-files", "-z"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(installer_mod.subprocess, "run", fake_run)
    warnings = installer_mod.adoption_preflight_warnings(tmp_path)

    assert any("plain.txt" in warning for warning in warnings)
    assert any("dir/line1\nline2.txt" in warning for warning in warnings)
    assert all("line2.txt; --create-adoption" not in warning for warning in warnings)


def test_create_adoption_ignores_ambient_git_dir_and_work_tree(tmp_path, monkeypatch):
    ambient = tmp_path / "ambient"
    target = tmp_path / "target"
    ambient.mkdir()
    target.mkdir()

    ambient_base = init_git_repo(ambient, "ambient.txt", "ambient\n", "ambient initial")
    target_base = init_git_repo(target, "target.txt", "target\n", "target initial")
    monkeypatch.setenv("GIT_DIR", str(ambient / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(ambient))

    installer = Installer(
        source=ROOT,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        create_adoption=True,
    )

    assert installer.install() == 0
    contract = json.loads(
        (target / ".ai" / "work-items" / "active" / "adopt_ai_cockpit.contract.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["baseCommit"] == target_base
    assert contract["baseCommit"] != ambient_base


def test_fresh_install_rejects_all_conflicting_managed_files_before_writing(tmp_path, capsys):
    common = tmp_path / "scripts" / "ai_common.py"
    doctor = tmp_path / "scripts" / "ai_doctor.py"
    common.parent.mkdir(parents=True)
    common.write_text("KEEP-COMMON\n", encoding="utf-8")
    doctor.write_text("KEEP-DOCTOR\n", encoding="utf-8")
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )

    assert installer.install() == 2
    error = capsys.readouterr().err
    assert "managed file conflicts detected" in error
    assert "scripts/ai_common.py" in error
    assert "scripts/ai_doctor.py" in error
    assert common.read_text(encoding="utf-8") == "KEEP-COMMON\n"
    assert doctor.read_text(encoding="utf-8") == "KEEP-DOCTOR\n"
    assert not (tmp_path / "Makefile.ai").exists()


def test_managed_installation_validation_checks_imports_and_make_entrypoint(tmp_path, monkeypatch):
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert installer.install() == 0
    monkeypatch.setattr(installer, "managed_copy_pairs", lambda: [])

    doctor = tmp_path / "scripts" / "ai_doctor.py"
    original_doctor = doctor.read_text(encoding="utf-8")
    doctor.write_text("import definitely_missing_ai_cockpit_module\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Python runtime import failed"):
        installer.validate_managed_installation()

    doctor.write_text(original_doctor, encoding="utf-8")
    (tmp_path / "Makefile.ai").write_text(
        "broken make syntax:\n\tunterminated ' quote\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Makefile.ai validation failed"):
        installer.validate_managed_installation()


def test_managed_installation_validation_ignores_host_scripts(tmp_path):
    rogue = tmp_path / "scripts" / "ai_rogue.py"
    rogue.parent.mkdir(parents=True)
    rogue.write_text("this is invalid python !!!\n", encoding="utf-8")

    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert installer.install() == 0
    assert rogue.read_text(encoding="utf-8") == "this is invalid python !!!\n"


def test_initial_status_uses_target_repository_changes(tmp_path):
    clean_target = tmp_path / "clean"
    dirty_target = tmp_path / "dirty"
    clean_target.mkdir()
    dirty_target.mkdir()
    init_git_repo(clean_target, "README.md", "# Target project\n", "initial")
    init_git_repo(dirty_target, "README.md", "# Target project\n", "initial")
    (dirty_target / "target_only.txt").write_text("target-only\n", encoding="utf-8")

    clean_installer = Installer(
        source=ROOT,
        target=clean_target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    dirty_installer = Installer(
        source=ROOT,
        target=dirty_target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )

    assert clean_installer.install() == 0
    assert dirty_installer.install() == 0
    clean_status = (clean_target / ".ai" / "cockpit" / "current_status.md").read_text(
        encoding="utf-8"
    )
    dirty_status = (dirty_target / ".ai" / "cockpit" / "current_status.md").read_text(
        encoding="utf-8"
    )
    clean_count = int(re.search(r"- Worktree Change Count: `(\d+)`", clean_status).group(1))
    dirty_count = int(re.search(r"- Worktree Change Count: `(\d+)`", dirty_status).group(1))
    assert clean_count == 0
    assert dirty_count == 0


def test_missing_stack_file_project_quality_targets_fail_closed(tmp_path):
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert installer.install() == 0
    (tmp_path / "Makefile.ai.stack").unlink()

    for target, message in (
        ("ai-cockpit-project-format-check", "ERROR: no project formatter configured"),
        ("ai-cockpit-project-test", "ERROR: no project test command configured"),
        ("ai-cockpit-project-lint", "ERROR: no project linter configured"),
    ):
        result = subprocess.run(
            ["make", target],
            cwd=tmp_path,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0
        assert message in result.stderr

    quality = subprocess.run(
        ["make", "quality"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert quality.returncode != 0


def test_upgrade_backs_up_policies_and_replaces_agent_marker_section(tmp_path):
    initial = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert initial.install() == 0
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8").replace("## AI Cockpit Rules", "## OLD RULES"),
        encoding="utf-8",
    )
    checks = tmp_path / ".ai" / "cockpit" / "checks.yaml"
    checks.write_text("# LOCAL CUSTOM CHECKS\n", encoding="utf-8")
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(
        gitignore.read_text(encoding="utf-8")
        .replace(".ai/work-items/active/*.review.json\n", "")
        .replace(".ai/cockpit/upgrade-backups/\n", ""),
        encoding="utf-8",
    )

    upgrade = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        upgrade=True,
    )
    assert upgrade.install() == 0

    upgraded_agents = agents.read_text(encoding="utf-8")
    assert "## OLD RULES" not in upgraded_agents
    assert "## AI Cockpit Rules" in upgraded_agents
    assert (tmp_path / ".ai" / "cockpit" / "version.json").is_file()
    backups = list(
        (tmp_path / ".ai" / "cockpit" / "upgrade-backups").glob("*/.ai/cockpit/checks.yaml")
    )
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "# LOCAL CUSTOM CHECKS\n"
    upgraded_ignore = gitignore.read_text(encoding="utf-8")
    assert ".ai/work-items/active/*.review.json" in upgraded_ignore
    assert ".ai/cockpit/upgrade-backups/" in upgraded_ignore

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    result = subprocess.run(
        ["git", "check-ignore", ".ai/cockpit/upgrade-backups/example/checks.yaml"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0

    contract = tmp_path / ".ai" / "work-items" / "active" / "upgrade_ai_cockpit.contract.json"
    summary = tmp_path / ".ai" / "work-items" / "active" / "upgrade_ai_cockpit.summary.json"
    assert contract.is_file()
    assert summary.is_file()
    contract_data = json.loads(contract.read_text(encoding="utf-8"))
    summary_data = json.loads(summary.read_text(encoding="utf-8"))
    assert contract_data["workItemId"] == "upgrade_ai_cockpit"
    assert "Automatic commit, push, PR, merge, or branch deletion" in contract_data["outOfScope"]
    assert summary_data["rollbackEvidence"]["backupRoot"].startswith(".ai/cockpit/upgrade-backups/")
    assert any(item["path"] == ".ai/cockpit/version.json" for item in summary_data["changedFiles"])


@pytest.mark.parametrize("name", ["AGENTS.md", "GEMINI.md", "CLAUDE.md"])
def test_upgrade_preserves_unmarked_agent_rules(tmp_path, name):
    custom_rules = "# Local Rules\n\nKEEP-ME\n"
    (tmp_path / name).write_text(custom_rules, encoding="utf-8")

    upgrade = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        upgrade=True,
    )

    assert upgrade.install() == 0
    upgraded = (tmp_path / name).read_text(encoding="utf-8")
    assert upgraded.startswith(custom_rules)
    assert "KEEP-ME" in upgraded
    assert "<!-- AI_COCKPIT_SECTION -->" in upgraded
    assert "<!-- /AI_COCKPIT_SECTION -->" in upgraded


def test_upgrade_branch_preparation_is_review_only(tmp_path, monkeypatch):
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=True,
        with_examples=False,
        update_makefile=False,
        upgrade=True,
    )
    monkeypatch.setattr(installer, "adopter_git_context", lambda: ("origin", "main"))
    assert installer.prepare_upgrade_branch() is True
    assert not (tmp_path / ".git").exists()
    monkeypatch.setenv("AI_COCKPIT_UPGRADE_BRANCH", "/invalid")
    assert installer.prepare_upgrade_branch() is False


def test_upgrade_branch_preparation_uses_remote_default_branch(tmp_path, monkeypatch):
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=False,
        upgrade=True,
    )
    monkeypatch.setattr(installer, "adopter_git_context", lambda: ("origin", "main"))
    monkeypatch.setattr(
        installer, "capture_git_head", lambda: installer_mod.GitHeadSnapshot("a" * 40, "main")
    )

    def fake_git(_target, args):
        if args[:2] == ["show-ref", "--verify"] and "refs/heads/" in args[-1]:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(installer_mod, "run_git", fake_git)
    assert installer.prepare_upgrade_branch() is True
    assert installer.created_adoption_branch == "upgrade/ai-cockpit"


def test_upgrade_preserves_diverged_project_owned_guard(tmp_path):
    guard = tmp_path / ".ai" / "guards" / "coverage_policy.yaml"
    guard.parent.mkdir(parents=True)
    guard.write_text("project-owned: true\n", encoding="utf-8")
    upgrade = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=False,
        upgrade=True,
    )
    assert upgrade.install() == 0
    assert guard.read_text(encoding="utf-8") == "project-owned: true\n"
    summary = json.loads(
        (tmp_path / ".ai/work-items/active/upgrade_ai_cockpit.summary.json").read_text()
    )
    assert any(
        item["path"] == ".ai/guards/coverage_policy.yaml" for item in summary["ownershipDecisions"]
    )


def test_upgrade_fails_closed_when_remote_default_branch_is_unknown(tmp_path):
    init_git_repo(tmp_path, "README.md", "project\n", "initial")
    run(tmp_path, "git", "remote", "add", "origin", "https://example.invalid/repo.git")
    upgrade = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=False,
        upgrade=True,
    )
    assert upgrade.install() == 2


def test_commented_makefile_include_does_not_suppress_active_include(tmp_path):
    makefile = tmp_path / "Makefile"
    makefile.write_text("# include Makefile.ai\n", encoding="utf-8")
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )

    assert installer.install() == 0
    lines = makefile.read_text(encoding="utf-8").splitlines()
    assert "# include Makefile.ai" in lines
    assert "include Makefile.ai" in lines


@pytest.mark.parametrize(
    ("force", "upgrade"),
    [(False, False), (True, False), (False, True)],
)
def test_reinstall_preserves_project_glossary_by_default(tmp_path, force, upgrade):
    initial = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert initial.install() == 0
    glossary = tmp_path / ".ai" / "glossary.md"
    glossary.write_text("# PROJECT GLOSSARY\n\nKEEP-ME\n", encoding="utf-8")

    reinstall = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=force,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        upgrade=upgrade,
    )

    assert reinstall.install() == 0
    assert glossary.read_text(encoding="utf-8") == "# PROJECT GLOSSARY\n\nKEEP-ME\n"


def test_replace_glossary_is_explicit_and_backed_up(tmp_path):
    custom = tmp_path / ".ai" / "glossary.md"
    custom.parent.mkdir(parents=True)
    custom.write_text("# PROJECT GLOSSARY\n\nKEEP-ME\n", encoding="utf-8")
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        replace_glossary=True,
    )

    assert installer.install() == 0
    assert custom.read_text(encoding="utf-8") == (ROOT / "templates" / "glossary.md").read_text(
        encoding="utf-8"
    )
    backups = list((tmp_path / ".ai" / "cockpit" / "upgrade-backups").glob("*/.ai/glossary.md"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "# PROJECT GLOSSARY\n\nKEEP-ME\n"


def test_install_warns_when_repository_has_no_initial_commit(tmp_path, capsys):
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )

    assert installer.install() == 0
    assert "ai-start requires a Git repository with at least one commit" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["upgrade", "force"])
@pytest.mark.parametrize(
    "malformed",
    [
        "before\n<!-- AI_COCKPIT_SECTION -->\ncritical user rule\n",
        "<!-- /AI_COCKPIT_SECTION -->\nbefore\n<!-- AI_COCKPIT_SECTION -->\n",
        "<!-- AI_COCKPIT_SECTION -->\n<!-- AI_COCKPIT_SECTION -->\n<!-- /AI_COCKPIT_SECTION -->\n",
        "<!-- AI_COCKPIT_SECTION -->\n<!-- /AI_COCKPIT_SECTION -->\n<!-- /AI_COCKPIT_SECTION -->\n",
    ],
)
def test_malformed_agent_markers_fail_before_writing(tmp_path, mode, malformed):
    agents = tmp_path / "AGENTS.md"
    agents.write_text(malformed, encoding="utf-8")
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=mode == "force",
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        upgrade=mode == "upgrade",
    )

    assert installer.install() == 2
    assert agents.read_text(encoding="utf-8") == malformed
    assert not (tmp_path / "Makefile.ai").exists()


def test_existing_common_make_target_is_preserved_without_override(tmp_path):
    makefile = tmp_path / "Makefile"
    makefile.write_text("project-test:\n\t@printf 'HOST TEST\\n'\n", encoding="utf-8")
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert installer.install() == 0
    result = subprocess.run(
        ["make", "project-test"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    clean_stdout = "\n".join(
        line
        for line in result.stdout.splitlines()
        if not (
            line.startswith("make[")
            and ("Entering directory" in line or "Leaving directory" in line)
        )
    ).strip()
    assert clean_stdout == "HOST TEST"
    assert "overriding commands" not in result.stderr


def test_reserved_make_target_conflict_fails_before_writing(tmp_path):
    makefile = tmp_path / "Makefile"
    original = "ai-cockpit-quality:\n\t@echo host\n"
    makefile.write_text(original, encoding="utf-8")
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert installer.install() == 2
    assert makefile.read_text(encoding="utf-8") == original
    assert not (tmp_path / "Makefile.ai").exists()


def test_upgrade_refuses_active_work_item_before_writing(tmp_path):
    initial = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert initial.install() == 0
    checks = tmp_path / ".ai" / "cockpit" / "checks.yaml"
    checks.write_text("# KEEP\n", encoding="utf-8")
    active = tmp_path / ".ai" / "work-items" / "active" / "open.contract.json"
    active.write_text("{}\n", encoding="utf-8")

    upgrade = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        upgrade=True,
    )

    assert upgrade.install() == 2
    assert checks.read_text(encoding="utf-8") == "# KEEP\n"
    assert not (tmp_path / ".ai" / "cockpit" / "upgrade-backups").exists()


def test_upgrade_with_active_requires_explicit_override(tmp_path):
    initial = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert initial.install() == 0
    active = tmp_path / ".ai" / "work-items" / "active" / "open.summary.json"
    active.write_text("{}\n", encoding="utf-8")

    upgrade = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        upgrade=True,
        upgrade_with_active=True,
    )

    assert upgrade.install() == 0


def test_upgrade_rejects_distribution_downgrade_before_writing(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / ".ai" / "cockpit").mkdir(parents=True)
    (target / ".ai" / "cockpit").mkdir(parents=True)
    (source / ".ai" / "cockpit" / "version.json").write_text(
        json.dumps({"distributionVersion": 2, "contractSchema": 2}), encoding="utf-8"
    )
    target_version = target / ".ai" / "cockpit" / "version.json"
    target_version.write_text(
        json.dumps({"distributionVersion": 3, "contractSchema": 2}), encoding="utf-8"
    )

    upgrade = Installer(
        source=source,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=False,
        upgrade=True,
    )

    assert upgrade.install() == 2
    assert json.loads(target_version.read_text(encoding="utf-8"))["distributionVersion"] == 3
    assert not (target / ".ai" / "cockpit" / "upgrade-backups").exists()


def test_upgrade_rejects_release_semver_downgrade_before_writing(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / ".ai" / "cockpit").mkdir(parents=True)
    (target / ".ai" / "cockpit").mkdir(parents=True)
    (source / ".ai" / "cockpit" / "version.json").write_text(
        json.dumps({"distributionVersion": 2, "contractSchema": 2, "releaseVersion": "0.5.22"}),
        encoding="utf-8",
    )
    target_version = target / ".ai" / "cockpit" / "version.json"
    target_version.write_text(
        json.dumps({"distributionVersion": 2, "contractSchema": 2, "releaseVersion": "0.5.23"}),
        encoding="utf-8",
    )

    upgrade = Installer(
        source=source,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=False,
        upgrade=True,
    )

    assert upgrade.install() == 2
    assert json.loads(target_version.read_text(encoding="utf-8"))["releaseVersion"] == "0.5.23"
    assert not (target / ".ai" / "cockpit" / "upgrade-backups").exists()


def test_upgrade_rejects_malformed_source_version_before_writing(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / ".ai" / "cockpit").mkdir(parents=True)
    (source / ".ai" / "cockpit" / "version.json").write_text(
        '{"distributionVersion": "two"}', encoding="utf-8"
    )

    upgrade = Installer(
        source=source,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=False,
        upgrade=True,
    )

    assert upgrade.install() == 2
    assert not target.exists()


def test_upgrade_rolls_back_when_post_copy_validation_fails(tmp_path, monkeypatch):
    initial = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert initial.install() == 0
    checks = tmp_path / ".ai" / "cockpit" / "checks.yaml"
    checks.write_text("# CUSTOM BEFORE UPGRADE\n", encoding="utf-8")

    upgrade = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        upgrade=True,
    )
    monkeypatch.setattr(
        upgrade,
        "validate_managed_installation",
        lambda: (_ for _ in ()).throw(ValueError("simulated validation failure")),
    )

    assert upgrade.install() == 2
    assert checks.read_text(encoding="utf-8") == "# CUSTOM BEFORE UPGRADE\n"


def test_install_and_upgrade_preserve_project_owned_profiles(tmp_path):
    profile = tmp_path / ".ai" / "project_profile.yaml"
    proposal = tmp_path / ".ai" / "project_profile.proposed.yaml"
    profile.parent.mkdir(parents=True)
    profile.write_text("version: 1\n# KEEP PROJECT BOUNDARY\n", encoding="utf-8")
    proposal.write_text("version: 1\n# KEEP PROPOSAL\n", encoding="utf-8")
    initial = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert initial.install() == 0
    assert "KEEP PROJECT BOUNDARY" in profile.read_text(encoding="utf-8")
    assert "KEEP PROPOSAL" in proposal.read_text(encoding="utf-8")

    upgrade = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        upgrade=True,
    )
    assert upgrade.install() == 0
    assert "KEEP PROJECT BOUNDARY" in profile.read_text(encoding="utf-8")
    assert "KEEP PROPOSAL" in proposal.read_text(encoding="utf-8")


def test_failed_upgrade_removes_new_gitignore(tmp_path, monkeypatch):
    initial = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert initial.install() == 0
    (tmp_path / ".gitignore").unlink()
    upgrade = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
        upgrade=True,
    )
    monkeypatch.setattr(
        upgrade,
        "validate_managed_installation",
        lambda: (_ for _ in ()).throw(ValueError("simulated validation failure")),
    )

    assert upgrade.install() == 2
    assert not (tmp_path / ".gitignore").exists()


def test_failed_initial_install_restores_original_tree(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text("# Existing\n", encoding="utf-8")
    preserved_empty = tmp_path / "preserved-empty"
    preserved_empty.mkdir()
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    monkeypatch.setattr(
        installer,
        "append_makefile_include",
        lambda: (_ for _ in ()).throw(ValueError("simulated late install failure")),
    )

    assert installer.install() == 2
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "# Existing\n"
    assert preserved_empty.is_dir()
    assert sorted(
        path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()
    ) == ["README.md"]
