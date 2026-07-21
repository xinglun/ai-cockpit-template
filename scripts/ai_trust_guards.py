#!/usr/bin/env python3
"""Deterministic Trust Layer capability, intent, constraint, and criteria guards."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ai_trust_schema import ValidationError, validate_payload
from ai_critical_domain_guards import critical_domain_signals


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES_PATH = PROJECT_ROOT / ".ai" / "project" / "capabilities.json"
SUCCESS_CRITERIA_PATH = PROJECT_ROOT / ".ai" / "project" / "success_criteria.json"


def display_path(path: Path) -> str:
    """Keep evidence portable and free of machine-specific absolute paths."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _signal(name: str, value: str, evidence: list[str], sources: list[str]) -> dict[str, Any]:
    return {"name": name, "value": value, "evidence": evidence, "sources": sources}


def _load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"cannot load {path}: {exc}"]


def capability_signal(contract: dict[str, Any], path: Path = CAPABILITIES_PATH) -> dict[str, Any]:
    payload, issues = _load_json(path)
    if issues:
        return _signal("Capability", "Missing", issues, [display_path(path)])
    if not isinstance(payload, dict):
        return _signal(
            "Capability", "Inconsistent", ["declaration must be an object"], [display_path(path)]
        )
    try:
        validate_payload("repository_capabilities", payload)
    except ValidationError as exc:
        return _signal("Capability", "Inconsistent", [str(exc)], [display_path(path)])

    capabilities = set(payload["capabilities"])
    required: set[str] = set()
    for raw_path in contract.get("scope", []):
        value = str(raw_path).lower()
        if "test" in value or value.startswith("tests/"):
            required.add("test_automation")
        if "doc" in value:
            required.add("documentation")
        if value.startswith("scripts/") or value == "makefile":
            required.add("software_design")
        if value.startswith(".ai/"):
            required.add("ai_governance")
    missing = sorted(required - capabilities)
    if missing:
        return _signal(
            "Capability",
            "Partial",
            [f"required capability is not declared: {item}" for item in missing],
            [display_path(path), "contract.scope"],
        )
    return _signal(
        "Capability",
        "Ready",
        [f"declared capabilities cover: {', '.join(sorted(required)) or 'the requested scope'}"],
        [display_path(path), "contract.scope"],
    )


_AMBIGUOUS_TERMS = re.compile(r"\b(?:something|maybe|somehow|as appropriate|if needed|etc)\b", re.I)

# This is deliberately a small boundary vocabulary.  Broad multilingual and hidden-risk
# interpretation is a separate Work Item; these explicit examples prevent scope-path
# relabeling from turning an obviously unsupported physical request into documentation work.
_UNSUPPORTED_OPERATION_TERMS = (
    "build a rocket",
    "make a rocket",
    "manufacture a rocket",
    "造一枚火箭",
    "制造火箭",
    "帮我制造武器",
    "制作炸弹",
    "build a bomb",
    "make a weapon",
    "ロケットを作って",
    "爆弾を作って",
)

_RAW_REQUEST_EXEMPTIONS = {
    "system_maintenance",
    "dependency_upgrade",
    "release_metadata",
    "internal_governance",
}
_RAW_REQUEST_SOURCE_TYPES = {"human", "issue", "pr_comment", "system"}


def _requires_raw_request(contract: dict[str, Any]) -> bool:
    scope = contract.get("scope")
    return (
        contract.get("contractVersion") == 2
        and contract.get("mode") == "code"
        and isinstance(scope, list)
        and any(isinstance(item, str) and ".ai/work-items/active/" in item for item in scope)
    )


def _raw_request_source_issues(contract: dict[str, Any]) -> list[str]:
    source = contract.get("rawRequestSource")
    if not isinstance(source, dict):
        return ["rawRequestSource must be declared when rawUserRequest is present"]
    issues: list[str] = []
    if source.get("type") not in _RAW_REQUEST_SOURCE_TYPES:
        issues.append("rawRequestSource.type must be human, issue, pr_comment, or system")
    for field in ("reference", "capturedAt", "digest"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            issues.append(f"rawRequestSource.{field} must be a non-empty string")
    return issues


def raw_request_signal(contract: dict[str, Any], path: Path = CAPABILITIES_PATH) -> dict[str, Any]:
    """Bind raw request evidence to declared intent and repository boundaries."""
    raw = contract.get("rawUserRequest")
    if raw is None:
        exemption = contract.get("rawRequestExemption")
        if _requires_raw_request(contract) and exemption not in _RAW_REQUEST_EXEMPTIONS:
            return _signal(
                "Raw Request",
                "Inconsistent",
                ["rawUserRequest is required for MODE=code Work Items"],
                ["contract.rawUserRequest", "contract.rawRequestExemption"],
            )
        if exemption in _RAW_REQUEST_EXEMPTIONS:
            return _signal(
                "Raw Request",
                "Not Applicable",
                [f"rawUserRequest is exempted for {exemption}"],
                ["contract.rawRequestExemption"],
            )
        return _signal(
            "Raw Request",
            "Not Applicable",
            ["no rawUserRequest is declared"],
            ["contract.rawUserRequest"],
        )
    if not isinstance(raw, str) or not raw.strip():
        return _signal(
            "Raw Request",
            "Inconsistent",
            ["rawUserRequest must be a non-empty string"],
            ["contract.rawUserRequest"],
        )
    source_issues = _raw_request_source_issues(contract)
    if source_issues:
        return _signal("Raw Request", "Inconsistent", source_issues, ["contract.rawRequestSource"])
    payload, issues = _load_json(path)
    if issues or not isinstance(payload, dict):
        return _signal(
            "Raw Request",
            "Inconsistent",
            issues or ["capability declaration must be an object"],
            [display_path(path)],
        )
    try:
        validate_payload("repository_capabilities", payload)
    except ValidationError as exc:
        return _signal("Raw Request", "Inconsistent", [str(exc)], [display_path(path)])
    declared = contract.get("declaredIntent")
    if not isinstance(declared, dict) or not isinstance(
        declared.get("requestedCapabilities"), list
    ):
        return _signal(
            "Raw Request",
            "Inconsistent",
            ["declaredIntent.requestedCapabilities must be declared before capability inference"],
            ["contract.declaredIntent"],
        )
    requested = {item for item in declared["requestedCapabilities"] if isinstance(item, str)}
    capabilities = set(payload["capabilities"])
    missing = sorted(requested - capabilities)
    if missing:
        return _signal(
            "Raw Request",
            "Inconsistent",
            [f"raw request declares unsupported capability: {item}" for item in missing],
            [display_path(path), "contract.declaredIntent"],
        )
    normalized = raw.casefold()
    matches = [term for term in _UNSUPPORTED_OPERATION_TERMS if term.casefold() in normalized]
    if matches:
        return _signal(
            "Raw Request",
            "Inconsistent",
            [
                f"unsupported operation must not be reframed as repository work: {', '.join(matches)}"
            ],
            ["contract.rawUserRequest", display_path(path)],
        )
    return _signal(
        "Raw Request",
        "Ready",
        ["raw request, declared intent, and repository capabilities are aligned"],
        ["contract.rawUserRequest", "contract.declaredIntent", display_path(path)],
    )


def intent_guard_signal(contract: dict[str, Any]) -> dict[str, Any]:
    intent = contract.get("intent")
    if not isinstance(intent, dict):
        return _signal(
            "Intent Guard", "Missing", ["contract.intent is missing"], ["contract.intent"]
        )
    values = [intent.get("problem"), intent.get("rationale")]
    constraints = intent.get("constraints", [])
    text = " ".join(str(item) for item in values if isinstance(item, str))
    text += " " + " ".join(str(item) for item in constraints if isinstance(item, str))
    if _AMBIGUOUS_TERMS.search(text):
        return _signal(
            "Intent Guard",
            "Partial",
            ["intent contains ambiguous wording that cannot determine implementation behavior"],
            ["contract.intent"],
        )
    return _signal(
        "Intent Guard",
        "Ready",
        ["intent is specific enough for deterministic review"],
        ["contract.intent"],
    )


def constraint_conflict_signal(contract: dict[str, Any]) -> dict[str, Any]:
    constraints = contract.get("intent", {}).get("constraints", [])
    if not isinstance(constraints, list):
        return _signal(
            "Constraint Guard",
            "Inconsistent",
            ["intent.constraints must be a list"],
            ["contract.intent.constraints"],
        )
    normalized = [
        str(item).strip().lower() for item in constraints if isinstance(item, str) and item.strip()
    ]
    conflicts: list[str] = []
    for left in normalized:
        for right in normalized:
            if left == right:
                continue
            left_tokens = set(re.findall(r"[a-z0-9_]+", left))
            right_tokens = set(re.findall(r"[a-z0-9_]+", right))
            shared = left_tokens & right_tokens
            if shared and (
                ("must not" in left and "must" in right) or ("never" in left and "always" in right)
            ):
                conflicts.append(
                    f"conflicting constraints share target terms: {', '.join(sorted(shared))}"
                )
    if conflicts:
        return _signal(
            "Constraint Guard",
            "Inconsistent",
            sorted(set(conflicts)),
            ["contract.intent.constraints"],
        )
    return _signal(
        "Constraint Guard",
        "Ready",
        ["declared constraints do not conflict"],
        ["contract.intent.constraints"],
    )


def success_criteria_signal(
    contract: dict[str, Any], path: Path = SUCCESS_CRITERIA_PATH
) -> dict[str, Any]:
    payload, issues = _load_json(path)
    if issues:
        return _signal("Success Criteria", "Missing", issues, [display_path(path)])
    if not isinstance(payload, dict):
        return _signal(
            "Success Criteria",
            "Inconsistent",
            ["declaration must be an object"],
            [display_path(path)],
        )
    try:
        validate_payload("success_criteria", payload)
    except ValidationError as exc:
        return _signal("Success Criteria", "Inconsistent", [str(exc)], [display_path(path)])
    if payload["workItemId"] != contract.get("workItemId"):
        return _signal(
            "Success Criteria",
            "Not Applicable",
            [f"no project-owned criteria are assigned to {contract.get('workItemId', '')}"],
            [display_path(path)],
        )
    criteria = payload["criteria"]
    incomplete = [item["id"] for item in criteria if not item.get("evidenceHints")]
    if incomplete:
        return _signal(
            "Success Criteria",
            "Partial",
            [f"criteria lack evidence hints: {', '.join(incomplete)}"],
            [display_path(path)],
        )
    return _signal(
        "Success Criteria",
        "Ready",
        [f"{len(criteria)} criteria have statements and evidence hints"],
        [display_path(path)],
    )


def trust_signals(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        raw_request_signal(contract),
        capability_signal(contract),
        intent_guard_signal(contract),
        constraint_conflict_signal(contract),
        success_criteria_signal(contract),
        *critical_domain_signals(contract),
    ]
