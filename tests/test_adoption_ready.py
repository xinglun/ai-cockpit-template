import subprocess
import sys
import shutil
from pathlib import Path

from ai_check_adoption_ready import readiness_failures


ROOT = Path(__file__).resolve().parents[1]


def write_ready_configuration(root: Path) -> None:
    (root / "Makefile.ai.stack").write_text(
        "PROJECT_FORMAT_CHECK = formatter --check\n"
        "PROJECT_TEST = test-runner\n"
        "PROJECT_LINT = linter\n",
        encoding="utf-8",
    )
    shutil.copytree(ROOT / ".ai", root / ".ai")
    guards = root / ".ai" / "guards"
    (guards / "coverage_policy.yaml").write_text(
        (ROOT / ".ai" / "guards" / "coverage_policy.yaml").read_text(encoding="utf-8").replace(
            "adoptionReviewed: false", "adoptionReviewed: true"
        ), encoding="utf-8",
    )
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ai.yml").write_text("run: make quality && make check-ai-pr\n", encoding="utf-8")


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
        [sys.executable, str(ROOT / "scripts" / "ai_check_adoption_ready.py"), "--root", str(tmp_path)],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0
    assert "static adoption configuration check passed" in result.stdout
    assert "does not prove command effectiveness" in result.stdout


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
        "# Later: make check-ai-pr\nrun: echo not-configured\n", encoding="utf-8",
    )

    assert any("check-ai-pr" in failure for failure in readiness_failures(tmp_path))


def test_trivial_quality_commands_do_not_satisfy_static_readiness(tmp_path):
    write_ready_configuration(tmp_path)
    (tmp_path / "Makefile.ai.stack").write_text(
        "PROJECT_FORMAT_CHECK = true\nPROJECT_TEST = true\nPROJECT_LINT = true\n",
        encoding="utf-8",
    )

    assert any("trivial no-op" in failure for failure in readiness_failures(tmp_path))
