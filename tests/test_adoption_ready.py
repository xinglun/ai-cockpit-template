import subprocess
import sys
import shutil
from pathlib import Path

from ai_check_adoption_ready import readiness_failures, template_exemption
from ai_readiness_policy import readiness_state


ROOT = Path(__file__).resolve().parents[1]


def test_readiness_separates_installation_from_production(tmp_path):
    (tmp_path / ".ai" / "cockpit").mkdir(parents=True)
    (tmp_path / ".ai" / "cockpit" / "version.json").write_text("{}", encoding="utf-8")
    assert readiness_state(tmp_path)["state"] == "adoption_installed"


def test_template_codeowners_uses_authorized_personal_owner():
    codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")

    assert "* @RayIori" in codeowners
    assert "@xinglun" not in codeowners


def test_adopter_configuration_requires_one_target_approval():
    documentation = (ROOT / "docs" / "getting-started" / "adopter-configuration.md").read_text(
        encoding="utf-8"
    )

    assert "at least one required approval" in documentation
    assert "replace\n  that identity" in documentation


def write_ready_configuration(root: Path) -> None:
    (root / "Makefile.ai.stack").write_text(
        "PROJECT_FORMAT_CHECK = formatter --check\n"
        "PROJECT_TEST = test-runner\n"
        "PROJECT_LINT = linter\n",
        encoding="utf-8",
    )
    shutil.copytree(ROOT / ".ai", root / ".ai")
    profile = root / ".ai" / "project_profile.yaml"
    profile.write_text(
        profile.read_text(encoding="utf-8").replace(
            "repositoryRole: template\n", "repositoryRole: adopted\n"
        ),
        encoding="utf-8",
    )
    guards = root / ".ai" / "guards"
    (guards / "coverage_policy.yaml").write_text(
        (ROOT / ".ai" / "guards" / "coverage_policy.yaml")
        .read_text(encoding="utf-8")
        .replace("adoptionReviewed: false", "adoptionReviewed: true"),
        encoding="utf-8",
    )
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ai.yml").write_text(
        "run: make ai-cockpit-quality && make check-ai-pr\n", encoding="utf-8"
    )
    (root / ".github" / "CODEOWNERS").write_text("* @governance-reviewers\n", encoding="utf-8")
    (root / "SECURITY.md").write_text(
        "# Security Policy\n\n"
        "Report vulnerabilities through the repository's private security channel.\n"
        "Supported versions and response expectations are maintained by the security team.\n",
        encoding="utf-8",
    )


def test_adopted_readiness_rejects_missing_external_approval_boundaries(tmp_path):
    write_ready_configuration(tmp_path)
    (tmp_path / ".github" / "CODEOWNERS").unlink()
    (tmp_path / "SECURITY.md").unlink()

    failures = readiness_failures(tmp_path)

    assert any("CODEOWNERS" in failure and "missing" in failure for failure in failures)
    assert any("SECURITY.md" in failure and "missing" in failure for failure in failures)


def test_adopted_readiness_rejects_current_template_placeholders(tmp_path):
    write_ready_configuration(tmp_path)
    (tmp_path / ".github" / "CODEOWNERS").write_text(
        "* @REPLACE_WITH_REPOSITORY_OWNER\n", encoding="utf-8"
    )
    (tmp_path / "SECURITY.md").write_text(
        "# Security Policy\n\n"
        "This repository is a governance template.\n"
        "Before production adoption, replace this file with your private reporting path.\n",
        encoding="utf-8",
    )

    failures = readiness_failures(tmp_path)

    assert any("CODEOWNERS" in failure for failure in failures)
    assert any("SECURITY.md" in failure for failure in failures)


def test_readiness_fails_with_all_actionable_configuration_gaps(tmp_path):
    failures = readiness_failures(tmp_path)

    assert len(failures) >= 4
    assert any("quality" in failure for failure in failures)
    assert any("adoptionReviewed: true" in failure for failure in failures)
    assert any("check-ai-pr" in failure for failure in failures)
    assert any("Project Profile" in failure for failure in failures)


def test_readiness_passes_only_after_explicit_configuration(tmp_path):
    write_ready_configuration(tmp_path)

    assert readiness_failures(tmp_path) == []
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "ai_check_adoption_ready.py"),
            "--root",
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "static adoption configuration check passed" in result.stdout
    assert "does not prove command effectiveness" in result.stdout
    assert "make ai-cockpit-quality and check-ai-pr" in result.stdout


def test_confirmed_template_profile_is_exempt_only_in_explicit_maintenance_mode(
    tmp_path, monkeypatch
):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    shutil.copytree(ROOT / "templates", tmp_path / "templates")
    monkeypatch.setenv("AI_COCKPIT_EXECUTION_MODE", "template_maintenance")
    assert readiness_failures(tmp_path) == []


def test_template_exemption_accepts_explicit_execution_mode_without_environment(
    tmp_path, monkeypatch
):
    profile = {"repositoryRole": "template"}
    for relative in (
        "templates/agents/AI_COCKPIT_RULES.md",
        "templates/glossary.md",
        "templates/make/Makefile.ai",
        ".ai/work-items/_templates/work_item_contract.example.json",
        ".ai/work-items/_templates/work_item_summary.example.json",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("evidence\n", encoding="utf-8")
    monkeypatch.delenv("AI_COCKPIT_EXECUTION_MODE", raising=False)

    exempt, evidence = template_exemption(profile, tmp_path, execution_mode="template_maintenance")

    assert exempt is True
    assert "AI_COCKPIT_EXECUTION_MODE=template_maintenance" in evidence


def test_template_role_without_maintenance_evidence_remains_fail_closed(tmp_path):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    profile = tmp_path / ".ai" / "project_profile.yaml"
    profile.write_text(profile.read_text(encoding="utf-8"), encoding="utf-8")
    assert any("template role is not enough" in item for item in readiness_failures(tmp_path))


def test_template_role_with_empty_template_dirs_remains_fail_closed(tmp_path, monkeypatch):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    (tmp_path / "templates").mkdir()
    (tmp_path / ".ai" / "work-items" / "_templates").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AI_COCKPIT_EXECUTION_MODE", "template_maintenance")

    assert any("template role is not enough" in item for item in readiness_failures(tmp_path))


def test_template_role_with_empty_template_evidence_remains_fail_closed(tmp_path, monkeypatch):
    shutil.copytree(ROOT / ".ai", tmp_path / ".ai")
    shutil.copytree(ROOT / "templates", tmp_path / "templates")
    monkeypatch.setenv("AI_COCKPIT_EXECUTION_MODE", "template_maintenance")

    for relative in (
        "templates/agents/AI_COCKPIT_RULES.md",
        "templates/glossary.md",
        "templates/make/Makefile.ai",
        ".ai/work-items/_templates/work_item_contract.example.json",
        ".ai/work-items/_templates/work_item_summary.example.json",
    ):
        (tmp_path / relative).write_text("", encoding="utf-8")

    assert any("template role is not enough" in item for item in readiness_failures(tmp_path))


def test_missing_role_is_fail_closed(tmp_path):
    write_ready_configuration(tmp_path)
    profile = tmp_path / ".ai" / "project_profile.yaml"
    profile.write_text(
        profile.read_text(encoding="utf-8").replace("repositoryRole: adopted\n", ""),
        encoding="utf-8",
    )
    assert any("missing role is fail-closed" in item for item in readiness_failures(tmp_path))


def test_generic_fail_closed_stack_is_not_adoption_ready(tmp_path):
    write_ready_configuration(tmp_path)
    (tmp_path / "Makefile.ai.stack").write_text(
        "PROJECT_TEST = printf 'ERROR: configure PROJECT_TEST' >&2; false\n",
        encoding="utf-8",
    )

    assert any("placeholders" in failure for failure in readiness_failures(tmp_path))


def test_ci_comment_does_not_satisfy_readiness(tmp_path):
    write_ready_configuration(tmp_path)
    (tmp_path / ".github" / "workflows" / "ai.yml").write_text(
        "# Later: make check-ai-pr\nrun: echo not-configured\n",
        encoding="utf-8",
    )

    assert any("check-ai-pr" in failure for failure in readiness_failures(tmp_path))


def test_placeholder_codeowners_remains_fail_closed(tmp_path):
    write_ready_configuration(tmp_path)
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @owner\n", encoding="utf-8")

    assert any("CODEOWNERS" in failure for failure in readiness_failures(tmp_path))


def test_template_security_doc_remains_fail_closed_after_adoption(tmp_path):
    write_ready_configuration(tmp_path)
    (tmp_path / "SECURITY.md").write_text(
        "# Security Policy\n\nReplace this document with your own security reporting process.\n",
        encoding="utf-8",
    )

    assert any("SECURITY.md" in failure for failure in readiness_failures(tmp_path))


def test_adopter_owned_codeowners_and_security_configuration_unblocks_readiness(tmp_path):
    write_ready_configuration(tmp_path)
    (tmp_path / ".github" / "CODEOWNERS").write_text(
        "# Repository-owned review team\n* @governance-reviewers\n",
        encoding="utf-8",
    )
    (tmp_path / "SECURITY.md").write_text(
        "# Security Policy\n\n"
        "Report vulnerabilities through the repository's private security channel.\n"
        "Supported versions and response expectations are maintained by the security team.\n",
        encoding="utf-8",
    )

    assert readiness_failures(tmp_path) == []


def test_trivial_quality_commands_do_not_satisfy_static_readiness(tmp_path):
    write_ready_configuration(tmp_path)
    (tmp_path / "Makefile.ai.stack").write_text(
        "PROJECT_FORMAT_CHECK = true\nPROJECT_TEST = true\nPROJECT_LINT = true\n",
        encoding="utf-8",
    )

    assert any("trivial no-op" in failure for failure in readiness_failures(tmp_path))
