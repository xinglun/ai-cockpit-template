import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cwd: Path, *command: str, env=None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def prepare_work_item(root: Path, task: str, changed: list[str], *, extra_checks=()) -> None:
    active = root / ".ai" / "work-items" / "active"
    contract_path = active / f"{task}.contract.json"
    summary_path = active / f"{task}.summary.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract.update(
        {
            "scope": [
                f".ai/work-items/active/{task}.contract.json",
                f".ai/work-items/active/{task}.summary.json",
                ".ai/work-items/archive/**",
                ".ai/cockpit/current_status.md",
                *changed,
            ],
            "outOfScope": [],
            "sources": [{"path": changed[0], "reason": "Documented project governance journey."}],
            "unknowns": [],
            "notCodable": False,
            "riskAssessment": {
                "level": "medium",
                "riskTypes": ["journey"],
                "reason": "Black-box journey fixture.",
            },
            "agentCapability": {
                "canImplement": True,
                "canVerify": True,
                "needsHumanDecision": False,
                "blockedReason": "",
            },
            "executionDecision": {
                "status": "continue",
                "reason": "Fixture decisions are explicit.",
            },
            "preReviewWarnings": ["Review fixture boundary ownership."],
            "acceptance": ["Configured behavior and governance checks pass."],
            "guidelines": ["Keep project changes covered by tests."],
            "restrictedWriteApproval": {
                "approved": True,
                "approvedBy": "journey fixture owner",
                "reason": "Explicit fixture calibration.",
            },
        }
    )
    existing = {item["check"] for item in contract["verification"]}
    contract["verification"].extend(
        {"check": check, "required": True} for check in extra_checks if check not in existing
    )
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()[:16]

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(
        {
            "changedFiles": [
                {
                    "path": f".ai/work-items/active/{task}.contract.json",
                    "reason": "Journey Contract.",
                },
                {
                    "path": f".ai/work-items/active/{task}.summary.json",
                    "reason": "Journey Summary.",
                },
                *({"path": path, "reason": "Journey project change."} for path in changed),
            ],
            "sourcesUsed": changed,
            "guidelinesCompliance": [
                {
                    "guideline": "Keep project changes covered by tests.",
                    "compliant": True,
                    "evidence": "make ai-cockpit-quality is required.",
                }
            ],
            "unknownsRemaining": [],
            "risk": {"level": "medium", "detail": "Fixture verifies the public lifecycle."},
            "generatedFiles": [],
            "destructiveChanges": [],
            "observedIssues": [],
            "residualRisks": [],
            "reviewReadiness": {
                "status": "ready",
                "reason": "Fixture inputs are explicit.",
                "expectedReviewFocus": ["Journey ownership"],
            },
            "boundaryChecks": {
                "runtimeEntrypoints": "verified",
                "userVisibleOutput": "verified",
                "persistence": "not_applicable",
                "localization": "not_applicable",
                "generatedArtifacts": "verified",
                "makeEntrypoints": "verified",
            },
            "checkpointEvidence": [
                {
                    "stage": stage,
                    "recorded": True,
                    "detail": "Journey checkpoint.",
                    "contractHash": contract_hash,
                    "acceptanceCount": 1,
                    "unknownCount": 0,
                    "requiredChecks": len(contract["verification"]),
                    "requiredChecksPassed": 0,
                }
                for stage in ("before_edit", "before_finish")
            ],
            "knownGaps": [],
            "overclaimPrevention": "The fixture proves only its generated minimal project.",
        }
    )
    for check in extra_checks:
        if not any(item.get("check") == check for item in summary["verification"]):
            summary["verification"].append({"check": check, "result": "not_run"})
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def confirmed_profile() -> str:
    return """version: 1
repositoryRole: adopted
detectedFacts:
  languages:
    - "python"
  frameworks: []
  buildSystems:
    - "python-packaging"
  infrastructure:
    - "github-actions"
suggestedBoundaries:
  productionRoots:
    - "src/**"
  featureRoots:
    - "src/**"
  testRoots:
    - "tests/**"
  generatedPaths:
    - "target/**"
  criticalPaths:
    - ".github/workflows/**"
approvedBoundaries:
  productionRoots:
    - "src/**"
  featureRoots:
    - "src/**"
  testRoots:
    - "tests/**"
  generatedPaths:
    - "target/**"
  criticalPaths:
    - ".github/workflows/**"
reviewRequirements:
  - "quality"
unknowns: []
evidence:
  - "python|confidence:high|evidence:pyproject.toml"
approval:
  reviewed: true
  reviewedBy: "fixture project owner"
  reason: "Fixture boundaries explicitly confirmed."
"""


def test_documented_project_governance_journey_and_upgrade_rollback(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    assert run(project, "git", "init", "-q").returncode == 0
    run(project, "git", "config", "user.email", "test@example.invalid")
    run(project, "git", "config", "user.name", "Journey")
    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / ".github" / "workflows").mkdir(parents=True)
    (project / "src" / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (project / "tests" / "test_app.py").write_text(
        "import unittest\nfrom src.app import add\nclass T(unittest.TestCase):\n    def test_add(self): self.assertEqual(add(1, 2), 3)\n",
        encoding="utf-8",
    )
    (project / "pyproject.toml").write_text(
        "[project]\nname='journey'\nversion='0.0.1'\n", encoding="utf-8"
    )
    (project / "Makefile").write_text("# Project commands\n", encoding="utf-8")
    (project / ".github" / "workflows" / "ci.yml").write_text(
        "run: make ai-cockpit-quality\n# separate job\nrun: make check-ai-pr\n", encoding="utf-8"
    )
    run(project, "git", "add", ".")
    assert run(project, "git", "commit", "-qm", "initial").returncode == 0
    base = run(project, "git", "rev-parse", "HEAD").stdout.strip()

    env = {**os.environ, "AI_COCKPIT_TEMPLATE_SOURCE": str(ROOT)}
    install = run(
        project,
        str(ROOT / "install.sh"),
        "--stack",
        "python",
        "--update-makefile",
        "--create-adoption",
        env=env,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    finish = run(project, "make", "ai-finish", "TASK=adopt_ai_cockpit", f"PYTHON={sys.executable}")
    assert finish.returncode == 0, finish.stdout + finish.stderr
    run(project, "git", "add", ".")
    assert run(project, "git", "commit", "-qm", "adopt cockpit").returncode == 0

    start = run(
        project,
        "make",
        "ai-start",
        "TASK=configure_ai_cockpit",
        "MODE=code",
        f"PYTHON={sys.executable}",
    )
    assert start.returncode == 0, start.stdout + start.stderr
    assert "Preflight Review" in start.stdout
    assert "Preflight Review requires attention before implementation." in start.stdout
    assert run(project, "make", "cockpit-doctor", f"PYTHON={sys.executable}").returncode == 0
    assert run(project, "make", "cockpit-calibrate", f"PYTHON={sys.executable}").returncode == 0
    (project / ".ai" / "project_profile.yaml").write_text(confirmed_profile(), encoding="utf-8")
    coverage = project / ".ai" / "guards" / "coverage_policy.yaml"
    coverage.write_text(
        coverage.read_text(encoding="utf-8").replace(
            "adoptionReviewed: false", "adoptionReviewed: true"
        ),
        encoding="utf-8",
    )
    (project / "Makefile.ai.stack").write_text(
        f'PROJECT_FORMAT_CHECK = git diff --check\nPROJECT_TEST = {sys.executable} -m unittest discover -s tests\nPROJECT_LINT = {sys.executable} -c \'compile(open("src/app.py").read(), "src/app.py", "exec")\'\n',
        encoding="utf-8",
    )
    prepare_work_item(
        project,
        "configure_ai_cockpit",
        [
            ".ai/project_profile.proposed.yaml",
            ".ai/project_profile.yaml",
            ".ai/guards/coverage_policy.yaml",
            "Makefile.ai.stack",
            ".github/CODEOWNERS",
            "SECURITY.md",
        ],
        extra_checks=("aiProjectProfile", "aiGuardCalibration"),
    )
    (project / ".github" / "CODEOWNERS").write_text("* @governance-reviewers\n", encoding="utf-8")
    (project / "SECURITY.md").write_text(
        "# Security Policy\n\n"
        "Report vulnerabilities through the repository's private security channel.\n"
        "Supported versions and response expectations are maintained by the security team.\n",
        encoding="utf-8",
    )
    assert (
        run(project, "make", "check-ai-adoption-ready", f"PYTHON={sys.executable}").returncode == 0
    )
    finish = run(
        project, "make", "ai-finish", "TASK=configure_ai_cockpit", f"PYTHON={sys.executable}"
    )
    assert finish.returncode == 0, finish.stdout + finish.stderr
    run(project, "git", "add", ".")
    assert run(project, "git", "commit", "-qm", "calibrate boundaries").returncode == 0

    start = run(
        project, "make", "ai-start", "TASK=normal_change", "MODE=code", f"PYTHON={sys.executable}"
    )
    assert start.returncode == 0, start.stdout + start.stderr
    assert "Preflight Review" in start.stdout
    assert "Preflight Review requires attention before implementation." in start.stdout
    (project / "src" / "app.py").write_text(
        "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    (project / "tests" / "test_app.py").write_text(
        "import unittest\nfrom src.app import add, subtract\nclass T(unittest.TestCase):\n    def test_math(self):\n        self.assertEqual(add(1, 2), 3)\n        self.assertEqual(subtract(3, 2), 1)\n",
        encoding="utf-8",
    )
    prepare_work_item(project, "normal_change", ["src/app.py", "tests/test_app.py"])
    finish = run(project, "make", "ai-finish", "TASK=normal_change", f"PYTHON={sys.executable}")
    assert finish.returncode == 0, finish.stdout + finish.stderr
    run(project, "git", "add", ".")
    assert run(project, "git", "commit", "-qm", "normal governed change").returncode == 0
    pr = run(project, "make", "check-ai-pr", f"AI_BASE_COMMIT={base}", f"PYTHON={sys.executable}")
    assert pr.returncode == 0, pr.stdout + pr.stderr

    profile_before = (project / ".ai" / "project_profile.yaml").read_bytes()
    upgrade = run(
        project,
        str(ROOT / "install.sh"),
        "--stack",
        "python",
        "--update-makefile",
        "--upgrade",
        env=env,
    )
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr
    assert (project / ".ai" / "project_profile.yaml").read_bytes() == profile_before

    broken_source = tmp_path / "broken-source"
    shutil.copytree(
        ROOT, broken_source, ignore=shutil.ignore_patterns(".git", ".venv", "target", "__pycache__")
    )
    broken_module = broken_source / "scripts" / "ai_check_scope.py"
    broken_module.write_text(
        broken_module.read_text(encoding="utf-8") + "\nthis is invalid python !!!\n",
        encoding="utf-8",
    )
    managed_before = (project / "scripts" / "ai_common.py").read_bytes()
    scope_before = (project / "scripts" / "ai_check_scope.py").read_bytes()
    failed_env = {**os.environ, "AI_COCKPIT_TEMPLATE_SOURCE": str(broken_source)}
    failed = run(
        project,
        str(broken_source / "install.sh"),
        "--stack",
        "python",
        "--update-makefile",
        "--upgrade",
        env=failed_env,
    )
    assert failed.returncode == 2
    assert (project / "scripts" / "ai_common.py").read_bytes() == managed_before
    assert (project / "scripts" / "ai_check_scope.py").read_bytes() == scope_before
    assert (project / ".ai" / "project_profile.yaml").read_bytes() == profile_before
