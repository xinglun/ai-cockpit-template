#!/usr/bin/env python3
"""Build and apply explicit, confirmation-aware project schema migrations."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from typing import Any


class MigrationError(ValueError):
    """Raised for invalid or unsupported migration inputs."""


def build_plan(
    config: dict[str, Any], *, from_version: int, to_version: int, registry: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(config, dict) or not isinstance(registry, dict):
        raise MigrationError("config and registry must be objects")
    versions = registry.get("versions")
    if not isinstance(versions, dict) or str(to_version) not in versions:
        raise MigrationError(f"target schema is unsupported: {to_version}")
    if from_version == to_version:
        return {
            "schemaVersion": 1,
            "fromVersion": from_version,
            "toVersion": to_version,
            "state": "no_change",
            "changes": [],
            "requiresHumanConfirmation": False,
            "rollback": "full",
        }
    transition = registry.get("transitions", {}).get(f"{from_version}->{to_version}")
    reverse = False
    if transition is None:
        reverse = registry.get("transitions", {}).get(f"{to_version}->{from_version}") is not None
        if reverse:
            return {
                "schemaVersion": 1,
                "fromVersion": from_version,
                "toVersion": to_version,
                "state": "partial_rollback",
                "changes": [],
                "requiresHumanConfirmation": True,
                "rollback": "partial_rollback",
                "blockingReason": "reverse migration is not supported automatically",
            }
        raise MigrationError(f"migration is unsupported: {from_version}->{to_version}")
    if not isinstance(transition, list):
        raise MigrationError("transition must be a list")
    changes: list[dict[str, Any]] = []
    requires = False
    for item in transition:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("old"), str)
            or not isinstance(item.get("new"), str)
        ):
            raise MigrationError("migration entry requires old and new fields")
        old, new = item["old"], item["new"]
        if old not in config and "default" not in item:
            changes.append(
                {
                    "oldField": old,
                    "newField": new,
                    "action": "blocked",
                    "reason": "old field missing and no default is defined",
                }
            )
            requires = True
            continue
        value = config.get(old, item.get("default"))
        action = "default" if old not in config else "auto"
        policy_impact = item.get("policyImpact", "none")
        if policy_impact in {"strengthen", "weaken", "critical_threshold", "baseline_change"}:
            action = "needs_human_confirmation"
            requires = True
        changes.append(
            {
                "oldField": old,
                "newField": new,
                "oldValue": config.get(old),
                "newValue": value,
                "defaultApplied": action == "default",
                "action": action,
                "policyImpact": policy_impact,
            }
        )
    state = "needs_human_confirmation" if requires else "ready"
    return {
        "schemaVersion": 1,
        "fromVersion": from_version,
        "toVersion": to_version,
        "state": state,
        "changes": changes,
        "requiresHumanConfirmation": requires,
        "rollback": "full" if not requires else "review_required",
        "reconfirmation": [
            item["newField"] for item in changes if item.get("action") == "needs_human_confirmation"
        ],
    }


def apply_plan(
    config: dict[str, Any], plan: dict[str, Any], *, confirm: bool = False
) -> dict[str, Any]:
    if plan.get("state") == "partial_rollback":
        return {
            "state": "partial_rollback",
            "config": deepcopy(config),
            "remainingManualActions": [
                plan.get("blockingReason", "reverse migration requires manual work")
            ],
            "written": False,
        }
    if plan.get("requiresHumanConfirmation") and not confirm:
        return {
            "state": "needs_human_confirmation",
            "config": deepcopy(config),
            "written": False,
            "changes": plan.get("changes", []),
            "reconfirmation": plan.get("reconfirmation", []),
        }
    result = deepcopy(config)
    for change in plan.get("changes", []):
        if change.get("action") == "blocked":
            return {
                "state": "blocked",
                "config": deepcopy(config),
                "written": False,
                "reason": change.get("reason"),
            }
        if change.get("action") in {"auto", "default"} or confirm:
            result[change["newField"]] = change.get("newValue")
            if change["oldField"] != change["newField"]:
                result.pop(change["oldField"], None)
    result["schemaVersion"] = plan["toVersion"]
    return {
        "state": "applied",
        "config": result,
        "written": True,
        "reconfirmation": plan.get("reconfirmation", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--from-version", type=int, required=True)
    parser.add_argument("--to-version", type=int, required=True)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    config = json.load(open(args.config, encoding="utf-8"))
    registry = json.load(open(args.registry, encoding="utf-8"))
    plan = build_plan(
        config, from_version=args.from_version, to_version=args.to_version, registry=registry
    )
    print(
        json.dumps(
            apply_plan(config, plan, confirm=args.confirm),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
