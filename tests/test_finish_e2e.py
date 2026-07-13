import hashlib
import json
import subprocess
import sys
from pathlib import Path

from install_ai_cockpit import Installer


ROOT = Path(__file__).resolve().parents[1]


def run(root: Path, *args: str, env=None):
    return subprocess.run(args, cwd=root, text=True, capture_output=True, env=env, check=False)


def prepare_work_item(tmp_path: Path, *, archive_collision: bool = False):
    (tmp_path / "Makefile").write_text("include Makefile.ai\n", encoding="utf-8")
    installer = Installer(
        source=ROOT,
        target=tmp_path,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=False,
    )
    assert installer.install() == 0
    (tmp_path / "Makefile.ai.stack").write_text(
        "PROJECT_FORMAT_CHECK = true\nPROJECT_TEST = true\nPROJECT_LINT = true\n",
        encoding="utf-8",
    )
    assert run(tmp_path, "git", "init", "-q", "-b", "main").returncode == 0
    run(tmp_path, "git", "config", "user.email", "test@example.invalid")
    run(tmp_path, "git", "config", "user.name", "Test")
    assert run(tmp_path, "git", "add", ".").returncode == 0
    assert run(tmp_path, "git", "commit", "-qm", "base").returncode == 0
    start = run(
        tmp_path,
        "make",
        "ai-start",
        "TASK=e2e",
        "TITLE=E2E",
        "MODE=code",
        f"PYTHON={sys.executable}",
    )
    assert start.returncode == 0, start.stdout + start.stderr
    assert "Preflight Review" in start.stdout

    contract_path = tmp_path / ".ai/work-items/active/e2e.contract.json"
    summary_path = tmp_path / ".ai/work-items/active/e2e.summary.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract.update(
        {
            "scope": ["fixture.txt", ".ai/cockpit/current_status.md", ".ai/work-items/archive/**"],
            "sources": ["test fixture"],
            "unknowns": [],
            "notCodable": False,
            "agentCapability": {
                "canImplement": True,
                "canVerify": True,
                "needsHumanDecision": False,
                "blockedReason": "",
            },
            "executionDecision": {"status": "continue", "reason": "E2E fixture is complete."},
            "acceptance": ["finish lifecycle behaves correctly"],
        }
    )
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()[:16]
    (tmp_path / "fixture.txt").write_text("changed\n", encoding="utf-8")
    changed = [{"path": "fixture.txt", "reason": "E2E lifecycle fixture."}]
    collision_path = (
        tmp_path
        / ".ai/work-items/archive"
        / str(__import__("datetime").datetime.now().year)
        / "e2e.contract.json"
    )
    if archive_collision:
        collision_path.parent.mkdir(parents=True, exist_ok=True)
        collision_path.write_text("{}\n", encoding="utf-8")
        changed.append(
            {
                "path": collision_path.relative_to(tmp_path).as_posix(),
                "reason": "Archive collision fixture.",
            }
        )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    guidelines_compliance = [
        {"guideline": g, "compliant": True, "evidence": "Verified E2E."}
        for g in contract.get("guidelines", [])
    ]
    summary.update(
        {
            "changedFiles": changed,
            "sourcesUsed": ["test fixture"],
            "unknownsRemaining": [],
            "risk": {"level": "low", "detail": "E2E fixture"},
            "generatedFiles": [],
            "destructiveChanges": [],
            "observedIssues": [],
            "residualRisks": [],
            "reviewReadiness": {"status": "ready", "reason": "fixture", "expectedReviewFocus": []},
            "guidelinesCompliance": guidelines_compliance,
            "knownGaps": [],
            "checkpointEvidence": [
                {
                    "stage": stage,
                    "recorded": True,
                    "detail": "fixture",
                    "contractHash": contract_hash,
                    "acceptanceCount": 1,
                    "unknownCount": 0,
                    "requiredChecks": len(contract["verification"]),
                    "requiredChecksPassed": 0,
                }
                for stage in ("before_edit", "before_finish")
            ],
        }
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return contract_path, collision_path


def test_required_failure_keeps_active_and_retry_archives(tmp_path):
    contract_path, _ = prepare_work_item(tmp_path)
    failed = run(
        tmp_path, "make", "ai-finish", "TASK=e2e", f"PYTHON={sys.executable}", "PROJECT_TEST=false"
    )
    assert failed.returncode != 0
    assert contract_path.exists()

    retried = run(
        tmp_path, "make", "ai-finish", "TASK=e2e", f"PYTHON={sys.executable}", "PROJECT_TEST=true"
    )
    assert retried.returncode == 0, retried.stdout + retried.stderr
    assert not contract_path.exists()
    assert list((tmp_path / ".ai/work-items/archive").rglob("e2e.contract.json"))


def test_archive_collision_fails_after_checks_and_preserves_active(tmp_path):
    contract_path, collision_path = prepare_work_item(tmp_path, archive_collision=True)
    result = run(
        tmp_path, "make", "ai-finish", "TASK=e2e", f"PYTHON={sys.executable}", "PROJECT_TEST=true"
    )
    assert result.returncode != 0
    assert "Target already exists" in result.stdout + result.stderr
    assert contract_path.exists()
    assert collision_path.exists()
