from __future__ import annotations

import json
from pathlib import Path

from ai_install_facts import write_fact_bundle
from ai_upgrade_proposal import ProposalError, build_proposal


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    old = tmp_path / "old"
    new = tmp_path / "new"
    current = tmp_path / "current"
    for root in (old, new, current):
        _write(root, "template.txt", "baseline\n")
        _write(root, ".ai/project_profile.yaml", "project: true\n")
        _write(
            root,
            ".ai/guards/policy.yaml",
            "# BEGIN AI COCKPIT MANAGED REGION: policy\nold\n# END AI COCKPIT MANAGED REGION: policy\n",
        )
    _write(current, ".ai/work-items/archive/2026/history.md", "historic\n")
    _write(old, "removed.txt", "remove me\n")
    _write(new, "template.txt", "candidate\n")
    _write(new, "added.txt", "new\n")
    _write(
        new,
        ".ai/guards/policy.yaml",
        "# BEGIN AI COCKPIT MANAGED REGION: policy\nnew\n# END AI COCKPIT MANAGED REGION: policy\n",
    )
    _write(current, "conflict.txt", "project edit\n")
    _write(old, "conflict.txt", "baseline conflict\n")
    _write(new, "conflict.txt", "candidate conflict\n")
    write_fact_bundle(
        source=old,
        target=current,
        distribution_version={
            "distributionVersion": "1.0.0",
            "releaseVersion": "1.0.0",
            "contractSchema": 2,
        },
    )
    return old, new, current


def test_three_way_proposal_covers_changes_and_is_read_only(tmp_path: Path) -> None:
    old, new, current = _fixture(tmp_path)
    before = (current / ".ai" / "install" / "version.json").read_bytes()
    proposal = build_proposal(
        old_template=old,
        new_template=new,
        current_project=current,
        upgrade_id="upgrade-1",
    )
    categories = {item["path"]: item["classification"] for item in proposal["changes"]}
    assert categories["template.txt"] == "safe_template_update"
    assert categories["added.txt"] == "new_template_file"
    assert categories["removed.txt"] == "removed_template_file"
    assert categories["conflict.txt"] == "conflict"
    assert categories[".ai/project_profile.yaml"] == "project_owned_file"
    assert categories[".ai/guards/policy.yaml"] == "shared_managed_region"
    assert categories[".ai/work-items/archive/2026/history.md"] == "historical_file"
    assert proposal["state"] == "needs_human_confirmation"
    assert proposal["readOnly"] is True
    assert (current / ".ai" / "install" / "version.json").read_bytes() == before


def test_proposal_can_be_written_only_to_explicit_proposal_output(tmp_path: Path) -> None:
    old, new, current = _fixture(tmp_path)
    output = tmp_path / ".ai" / "upgrade" / "proposals" / "upgrade-2.json"
    proposal = build_proposal(
        old_template=old, new_template=new, current_project=current, upgrade_id="upgrade-2"
    )
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps(proposal), encoding="utf-8")
    assert json.loads(output.read_text(encoding="utf-8"))["proposalId"] == "upgrade-2"


def test_invalid_release_evidence_fails_closed(tmp_path: Path) -> None:
    old, new, current = _fixture(tmp_path)
    evidence = tmp_path / "release.json"
    evidence.write_text("{}", encoding="utf-8")
    try:
        build_proposal(
            old_template=old,
            new_template=new,
            current_project=current,
            upgrade_id="upgrade-3",
            release_evidence=evidence,
        )
    except ProposalError as exc:
        assert "release evidence requires" in str(exc)
    else:
        raise AssertionError("invalid release evidence must fail closed")
