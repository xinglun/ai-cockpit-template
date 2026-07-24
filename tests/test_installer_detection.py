from __future__ import annotations

import json
from pathlib import Path

from ai_installer_detection import (
    InstallationPlan,
    detect_installation,
    serialize_plan,
)
from ai_installer_repository import RepositoryFacts


def facts(**overrides: object) -> RepositoryFacts:
    values: dict[str, object] = {
        "root": Path("/tmp/project"),
        "commit": "abc123",
        "branch": "main",
        "remote": "origin",
        "remote_url": "https://example.invalid/project.git",
        "default_branch": "main",
        "clean": True,
        "tracked_hygiene": (),
        "conflicts": (),
        "active_work_items": (),
        "symlink_risks": (),
    }
    values.update(overrides)
    return RepositoryFacts(**values)


def test_new_adoption_does_not_require_existing_work_item() -> None:
    result = detect_installation(
        facts=facts(active_work_items=()),
        mode="new_adoption",
        available_tools={"git", "python", "make", "curl", "sh"},
        stacks={"python"},
    )

    assert result.readiness == "ready_for_confirmation"
    assert result.plan.recommendation == "new_adoption"
    assert result.plan.write_boundary == "none_before_confirmation"


def test_upgrade_reports_active_items_and_conflicts() -> None:
    result = detect_installation(
        facts=facts(
            active_work_items=("existing.contract.json",),
            conflicts=("AGENTS.md",),
            clean=False,
        ),
        mode="upgrade",
        available_tools={"git"},
        stacks={"python"},
    )

    assert result.readiness == "blocked"
    assert "active_work_items" in result.blocking_reasons
    assert "conflicts" in result.blocking_reasons
    assert result.plan.stop_condition


def test_symlink_and_missing_tool_signals_are_explicit() -> None:
    result = detect_installation(
        facts=facts(symlink_risks=(".ai",)),
        mode="new_adoption",
        available_tools={"git"},
        stacks=set(),
    )

    assert "make" in result.missing_tools
    assert "symlink_risk" in result.blocking_reasons
    assert result.plan.impact == "high"


def test_plan_serialization_is_deterministic_and_contains_operator_fields() -> None:
    result = detect_installation(
        facts=facts(),
        mode="new_adoption",
        available_tools={"git", "python"},
        stacks={"python", "go"},
    )
    payload = serialize_plan(result.plan)

    assert payload == serialize_plan(result.plan)
    decoded = json.loads(payload)
    assert set(decoded) == {
        "facts",
        "recommendation",
        "impact",
        "examples",
        "writeBoundary",
        "expectedResult",
        "stopCondition",
        "checklist",
    }
    assert isinstance(result.plan, InstallationPlan)
