import json
import subprocess
import sys
from pathlib import Path

import install_ai_cockpit
import ai_disable_enable
import ai_rollback
import ai_uninstall_proposal
from install_ai_cockpit import Installer, SCRIPT_NAMES


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SCRIPTS = {
    "ai_install_status.py",
    "ai_lifecycle_facts.py",
    "ai_upgrade_proposal.py",
    "ai_upgrade_apply.py",
    "ai_rollback.py",
    "ai_disable_enable.py",
    "ai_uninstall_proposal.py",
}
RUNTIME_TARGETS = (
    "ai-cockpit-version",
    "ai-lifecycle-facts",
    "ai-cockpit-update-check",
    "ai-cockpit-update-propose",
    "ai-cockpit-update-apply",
    "ai-cockpit-rollback-propose",
    "ai-cockpit-disable",
    "ai-cockpit-enable",
    "ai-cockpit-uninstall-propose",
)


def test_installer_copy_map_contains_every_runtime_script():
    assert RUNTIME_SCRIPTS <= SCRIPT_NAMES
    assert all((ROOT / "scripts" / name).is_file() for name in RUNTIME_SCRIPTS)


def test_installed_adopter_contains_runtime_scripts_and_targets(tmp_path):
    target = tmp_path / "adopter"
    installer = Installer(
        source=ROOT,
        target=target,
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=True,
    )
    assert installer.install() == 0
    assert all((target / "scripts" / name).is_file() for name in RUNTIME_SCRIPTS)
    makefile = (target / "Makefile.ai").read_text(encoding="utf-8")
    assert all(f"{name}:" in makefile for name in RUNTIME_TARGETS)
    result = subprocess.run(
        ["make", "-f", "Makefile.ai", "-n", *RUNTIME_TARGETS],
        cwd=target,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_installer_fails_closed_when_runtime_script_is_not_available(monkeypatch, tmp_path):
    monkeypatch.setattr(
        install_ai_cockpit,
        "SCRIPT_NAMES",
        SCRIPT_NAMES - {"ai_install_status.py"},
    )
    installer = Installer(
        source=ROOT,
        target=tmp_path / "adopter",
        stack="generic",
        force=False,
        dry_run=False,
        with_examples=False,
        update_makefile=False,
    )
    assert installer.install() == 2


def test_installed_runtime_cli_entrypoints_write_proposals(monkeypatch, tmp_path):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"state": "active"}), encoding="utf-8")
    disable_output = tmp_path / "disable.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_disable_enable.py", "disable", "--state", str(state), "--output", str(disable_output)],
    )
    assert ai_disable_enable.main() == 0
    assert json.loads(disable_output.read_text(encoding="utf-8"))["state"] == "disabled"

    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({"sessionId": "test", "runtimeFiles": []}), encoding="utf-8")
    uninstall_output = tmp_path / "uninstall.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_uninstall_proposal.py", "--facts", str(facts), "--output", str(uninstall_output)],
    )
    assert ai_uninstall_proposal.main() == 0
    assert (
        json.loads(uninstall_output.read_text(encoding="utf-8"))["state"]
        == "needs_human_confirmation"
    )

    install_root = tmp_path / "installed"
    (install_root / ".ai" / "install").mkdir(parents=True)
    (install_root / ".ai" / "install" / "manifest.json").write_text("{}", encoding="utf-8")
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text("{}", encoding="utf-8")
    rollback_output = tmp_path / "rollback.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_rollback.py",
            "--snapshot",
            str(snapshot),
            "--current-root",
            str(install_root),
            "--output",
            str(rollback_output),
        ],
    )
    assert ai_rollback.main() == 2
    assert json.loads(rollback_output.read_text(encoding="utf-8"))["state"] == "blocked"


def test_runtime_surface_does_not_claim_calibration_or_quick_install():
    makefile = (ROOT / "templates" / "make" / "Makefile.ai").read_text(encoding="utf-8")
    assert "ai-calibrate" not in makefile
    assert "quick-install" not in makefile
