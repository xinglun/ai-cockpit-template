"""Plan and execute fail-closed rollback of an installed lifecycle update."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any


class RollbackError(ValueError):
    """Raised when rollback evidence is invalid."""


def _digest(value: Any) -> str:
    import json

    return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def build_snapshot(
    upgrade_id: str,
    manifest: dict[str, Any],
    version: dict[str, Any],
    managed_regions: dict[str, Any],
    runtime_files: dict[str, str],
    project_config: dict[str, Any],
    migration_plan: dict[str, Any],
    instructions: list[str],
) -> dict[str, Any]:
    """Create a self-contained, hashable snapshot without writing files."""
    if not upgrade_id or not isinstance(manifest, dict) or not isinstance(version, dict):
        raise RollbackError("invalid snapshot identity or manifest")
    if not isinstance(managed_regions, dict) or not isinstance(runtime_files, dict):
        raise RollbackError("managed regions and runtime files are required")
    return {
        "schemaVersion": 1,
        "upgradeId": upgrade_id,
        "manifest.before.json": deepcopy(manifest),
        "version.before.json": deepcopy(version),
        "managed-regions.before.json": deepcopy(managed_regions),
        "runtime": deepcopy(runtime_files),
        "projectConfigHash": _digest(project_config),
        "migrationPlan": deepcopy(migration_plan),
        "rollbackInstructions": list(instructions),
        "snapshotHash": _digest(
            {"upgradeId": upgrade_id, "manifest": manifest, "version": version}
        ),
    }


def plan_rollback(
    snapshot: dict[str, Any] | None, current: dict[str, Any], project_config: dict[str, Any]
) -> dict[str, Any]:
    """Return a proposal; this function never mutates current state."""
    if not snapshot:
        return {
            "state": "blocked",
            "reason": "snapshot_missing",
            "writes": [],
            "resumeCondition": "restore a verified snapshot",
        }
    if current.get("manifestHash") != snapshot.get("manifest.before.json", {}).get("manifestHash"):
        return {
            "state": "blocked",
            "reason": "current_installation_drift",
            "writes": [],
            "resumeCondition": "reconcile current installation facts",
        }
    migration = snapshot.get("migrationPlan", {})
    state = (
        "partial_rollback"
        if migration.get("rollback") == "partial_rollback"
        else "needs_human_confirmation"
    )
    return {
        "state": state,
        "reason": "migration_not_invertible"
        if state == "partial_rollback"
        else "explicit_confirmation_required",
        "upgradeId": snapshot["upgradeId"],
        "projectConfigPreserved": _digest(project_config) != snapshot.get("projectConfigHash"),
        "writes": ["runtime", "managed-regions", "version", "manifest"],
        "resumeCondition": "confirm proposal and resolve any residual manual instructions",
        "residualInstructions": snapshot.get("rollbackInstructions", []),
    }


def execute_rollback(
    snapshot: dict[str, Any] | None,
    proposal: dict[str, Any],
    current: dict[str, Any],
    project_config: dict[str, Any],
    confirm: bool = False,
) -> dict[str, Any]:
    """Restore owned content only after proposal and confirmation checks."""
    if proposal.get("state") in {"blocked", "partial_rollback"}:
        return {
            "state": proposal["state"],
            "writes": [],
            "residualInstructions": proposal.get("residualInstructions", []),
        }
    if not confirm:
        return {"state": "needs_human_confirmation", "writes": []}
    if not snapshot or current.get("manifestHash") != snapshot.get("manifest.before.json", {}).get(
        "manifestHash"
    ):
        return {"state": "blocked", "reason": "drift_detected", "writes": []}
    restored = deepcopy(current)
    restored.update(
        {
            "runtime": deepcopy(snapshot["runtime"]),
            "managedRegions": deepcopy(snapshot["managed-regions.before.json"]),
            "version": deepcopy(snapshot["version.before.json"]),
            "manifest": deepcopy(snapshot["manifest.before.json"]),
        }
    )
    return {
        "state": "rolled_back",
        "writes": ["runtime", "managed-regions", "version", "manifest"],
        "stateAfter": restored,
        "projectConfig": deepcopy(project_config),
    }
