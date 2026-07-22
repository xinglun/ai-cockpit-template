from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ai_install_facts import write_fact_bundle
from ai_upgrade_apply import apply_proposal


def _write(root: Path, path: str, content: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "project"
    candidate = tmp_path / "candidate"
    _write(root, "safe.txt", "old\n")
    _write(root, ".ai/project_profile.yaml", "project: true\n")
    _write(candidate, "safe.txt", "new\n")
    _write(candidate, ".ai/project_profile.yaml", "project: true\n")
    write_fact_bundle(
        source=candidate,
        target=root,
        distribution_version={
            "distributionVersion": "1",
            "releaseVersion": "1",
            "contractSchema": 2,
        },
    )
    current = _digest(root / "safe.txt")
    proposal = {
        "schemaVersion": 1,
        "proposalId": "upgrade-apply-test",
        "state": "ready_for_confirmation",
        "readOnly": True,
        "source": {"newTemplate": str(candidate)},
        "changes": [
            {"path": "safe.txt", "classification": "safe_template_update", "currentDigest": current}
        ],
    }
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
    return root, candidate, proposal_path


def test_unconfirmed_apply_is_zero_write(tmp_path: Path) -> None:
    root, _, proposal = _fixture(tmp_path)
    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    result = apply_proposal(proposal, root=root)
    after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    assert result["state"] == "needs_human_confirmation"
    assert {item["id"] for item in result["options"]} == {
        "apply_safe_updates",
        "exclude_files",
        "cancel",
        "change_target_version",
        "review_migration",
        "return",
    }
    assert before == after
    assert (root / "safe.txt").read_text() == "old\n"


def test_confirmed_apply_snapshots_and_preserves_project_content(tmp_path: Path) -> None:
    root, _, proposal = _fixture(tmp_path)
    result = apply_proposal(proposal, root=root, confirmation="APPLY")
    assert result["state"] == "applied"
    assert (root / "safe.txt").read_text() == "new\n"
    assert (root / ".ai" / "project_profile.yaml").read_text() == "project: true\n"
    assert (
        root / ".ai" / "upgrade" / "snapshots" / "upgrade-apply-test" / "manifest.before.json"
    ).is_file()
    assert [step["name"] for step in result["steps"]] == [
        "drift",
        "snapshot",
        "safe_files",
        "new_files",
        "removed_files",
        "shared_regions",
        "project_owned_retained",
        "migration",
        "generated_regeneration",
        "manifest_update",
        "integrity",
        "adoption_readiness",
        "smoke_test",
    ]


def test_drift_blocks_apply_without_writing(tmp_path: Path) -> None:
    root, _, proposal = _fixture(tmp_path)
    (root / "safe.txt").write_text("drift\n", encoding="utf-8")
    result = apply_proposal(proposal, root=root, confirmation="APPLY")
    assert result["state"] == "blocked"
    assert not (root / ".ai" / "upgrade" / "snapshots" / "upgrade-apply-test").exists()
    assert (root / "safe.txt").read_text() == "drift\n"
