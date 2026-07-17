#!/usr/bin/env python3
"""Generate and validate a Preflight Review for the active Work Item."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_common import (
    PROJECT_ROOT,
    load_json,
    simple_yaml_lists,
    simple_yaml_scalars,
    validate_scenario_coverage,
)
from ai_readiness_policy import has_explicit_blocker


ALLOWED_STATUSES = {"ready", "needs_human_confirmation", "not_ready"}
ALLOWED_SIGNAL_VALUES = {
    "Ready",
    "Partial",
    "Missing",
    "Weak",
    "Broad",
    "Suspiciously Empty",
    "Inconsistent",
    "Not Applicable",
}
DEFAULT_OUTPUT = PROJECT_ROOT / "target" / "ai_preflight_review.json"
DEFAULT_POLICY = PROJECT_ROOT / ".ai" / "guards" / "preflight_review_policy.yaml"


@dataclass(frozen=True)
class Signal:
    name: str
    value: str
    evidence: list[str]
    sources: list[str]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [item.strip() for item in values if isinstance(item, str) and item.strip()]


def _is_truthy(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value in policy: {value!r}")


def contract_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def policy_hash(path: Path) -> str:
    if not path.exists():
        return "defaults"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_policy(path: Path) -> dict[str, Any]:
    scalars = simple_yaml_scalars(path)
    lists = simple_yaml_lists(path)
    version = scalars.get("version", "1")
    gate_enabled = _is_truthy(scalars.get("gateEnabled"), default=False)
    blocked_statuses = [item for item in lists.get("blockedStatuses", []) if non_empty_string(item)]
    return {
        "path": path.as_posix(),
        "version": version,
        "gateEnabled": gate_enabled,
        "blockedStatuses": blocked_statuses,
        "raw": {"scalars": scalars, "lists": lists},
    }


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def source_value(source: Any) -> tuple[str, str]:
    if not isinstance(source, dict):
        return "", ""
    path = source.get("path")
    reason = source.get("reason")
    return (
        str(path).strip() if non_empty_string(path) else "",
        str(reason).strip() if non_empty_string(reason) else "",
    )


def is_placeholder_source(path: str) -> bool:
    lowered = path.lower()
    return any(token in lowered for token in ("replace-with", "example", "placeholder", "todo"))


def scope_signal(contract: dict[str, Any]) -> Signal:
    scope = contract.get("scope")
    out_of_scope = _string_list(contract.get("outOfScope"))
    if not isinstance(scope, list):
        return Signal(
            "Scope",
            "Missing",
            ["contract.scope is missing"],
            ["contract.scope"],
        )

    scope_paths = _string_list(scope)
    if len(scope_paths) != len(scope):
        return Signal(
            "Scope",
            "Inconsistent",
            ["contract.scope contains a non-string or empty entry"],
            ["contract.scope"],
        )
    if not scope_paths:
        return Signal(
            "Scope",
            "Missing",
            ["contract.scope is empty"],
            ["contract.scope"],
        )

    overlap = sorted(set(scope_paths).intersection(out_of_scope))
    if overlap:
        return Signal(
            "Scope",
            "Inconsistent",
            [f"scope overlaps outOfScope: {', '.join(overlap)}"],
            ["contract.scope", "contract.outOfScope"],
        )

    broad_patterns = [item for item in scope_paths if item in {"*", "**"}]
    if broad_patterns:
        return Signal(
            "Scope",
            "Broad",
            [f"scope contains broad pattern(s): {', '.join(broad_patterns)}"],
            ["contract.scope"],
        )

    return Signal(
        "Scope",
        "Ready",
        [f"scope declares {len(scope_paths)} path pattern(s)"],
        ["contract.scope"],
    )


def out_of_scope_signal(contract: dict[str, Any]) -> Signal:
    out_of_scope = contract.get("outOfScope")
    if not isinstance(out_of_scope, list):
        return Signal(
            "Out Of Scope",
            "Missing",
            ["contract.outOfScope is missing"],
            ["contract.outOfScope"],
        )
    entries = _string_list(out_of_scope)
    if len(entries) != len(out_of_scope):
        return Signal(
            "Out Of Scope",
            "Inconsistent",
            ["contract.outOfScope contains a non-string or empty entry"],
            ["contract.outOfScope"],
        )
    if not entries:
        return Signal(
            "Out Of Scope",
            "Not Applicable",
            ["no exclusions were declared"],
            ["contract.outOfScope"],
        )
    return Signal(
        "Out Of Scope",
        "Ready",
        [f"outOfScope declares {len(entries)} exclusion(s)"],
        ["contract.outOfScope"],
    )


def intent_signal(contract: dict[str, Any]) -> Signal:
    intent = contract.get("intent")
    if not isinstance(intent, dict):
        return Signal(
            "Intent",
            "Missing",
            ["contract.intent is missing"],
            ["contract.intent"],
        )

    problems = []
    present: list[str] = []

    problem = intent.get("problem")
    if non_empty_string(problem):
        present.append("problem")
    elif problem is not None:
        problems.append("contract.intent.problem is empty")

    constraints = intent.get("constraints")
    if isinstance(constraints, list):
        constraint_values = _string_list(constraints)
        if constraint_values:
            present.append("constraints")
        elif constraints:
            problems.append("contract.intent.constraints contains an empty entry")
    elif constraints is not None:
        problems.append("contract.intent.constraints must be a list")

    rationale = intent.get("rationale")
    if non_empty_string(rationale):
        present.append("rationale")
    elif rationale is not None:
        problems.append("contract.intent.rationale is empty")

    if problems:
        return Signal("Intent", "Inconsistent", problems, ["contract.intent"])
    if not present:
        return Signal(
            "Intent",
            "Missing",
            ["contract.intent has no meaningful content"],
            ["contract.intent"],
        )
    if len(present) == 3:
        return Signal(
            "Intent",
            "Ready",
            ["problem, constraints, and rationale are all present"],
            ["contract.intent.problem", "contract.intent.constraints", "contract.intent.rationale"],
        )
    return Signal(
        "Intent",
        "Partial",
        [f"intent has {len(present)} of 3 required evidence element(s): {', '.join(present)}"],
        ["contract.intent.problem", "contract.intent.constraints", "contract.intent.rationale"],
    )


def unknowns_signal(contract: dict[str, Any]) -> Signal:
    risk = _dict(contract.get("riskAssessment"))
    level = risk.get("level")
    unknowns = contract.get("unknowns")
    if not isinstance(unknowns, list):
        return Signal(
            "Unknowns",
            "Missing",
            ["contract.unknowns is missing"],
            ["contract.unknowns", "contract.riskAssessment"],
        )
    values = _string_list(unknowns)
    if len(values) != len(unknowns):
        return Signal(
            "Unknowns",
            "Inconsistent",
            ["contract.unknowns contains a non-string or empty entry"],
            ["contract.unknowns", "contract.riskAssessment"],
        )
    if not values:
        if level in {"medium", "high"}:
            return Signal(
                "Unknowns",
                "Suspiciously Empty",
                [f"riskAssessment.level is {level} but unknowns is empty"],
                ["contract.unknowns", "contract.riskAssessment"],
            )
        return Signal(
            "Unknowns",
            "Ready",
            ["no unknowns are declared for a low-risk Work Item"],
            ["contract.unknowns", "contract.riskAssessment"],
        )
    return Signal(
        "Unknowns",
        "Partial",
        [f"{len(values)} unknown(s) remain open"],
        ["contract.unknowns", "contract.riskAssessment"],
    )


def _acceptance_item_is_broad(item: str) -> bool:
    lowered = item.lower()
    vague_phrases = (
        "done",
        "implemented",
        "works",
        "properly",
        "correctly",
        "as needed",
        "if needed",
        "if necessary",
        "appropriate",
        "updated",
        "documented",
        "reviewed",
        "fixed",
        "improved",
        "requirements",
        "etc",
    )
    if any(phrase in lowered for phrase in vague_phrases):
        return True
    words = [word for word in item.replace("/", " ").replace("-", " ").split() if word]
    return len(words) <= 5


def acceptance_signal(contract: dict[str, Any]) -> Signal:
    acceptance = contract.get("acceptance")
    if not isinstance(acceptance, list):
        return Signal(
            "Acceptance",
            "Missing",
            ["contract.acceptance is missing"],
            ["contract.acceptance"],
        )
    values = _string_list(acceptance)
    if len(values) != len(acceptance):
        return Signal(
            "Acceptance",
            "Inconsistent",
            ["contract.acceptance contains a non-string or empty entry"],
            ["contract.acceptance"],
        )
    if not values:
        return Signal(
            "Acceptance",
            "Missing",
            ["contract.acceptance is empty"],
            ["contract.acceptance"],
        )

    broad_items = [item for item in values if _acceptance_item_is_broad(item)]
    if len(broad_items) == len(values):
        return Signal(
            "Acceptance",
            "Broad",
            [f"acceptance is too broad: {', '.join(broad_items[:3])}"],
            ["contract.acceptance"],
        )
    if broad_items:
        return Signal(
            "Acceptance",
            "Partial",
            [f"{len(broad_items)} acceptance item(s) are broad or underspecified"],
            ["contract.acceptance"],
        )
    return Signal(
        "Acceptance",
        "Ready",
        [f"acceptance declares {len(values)} concrete item(s)"],
        ["contract.acceptance"],
    )


def sources_signal(contract: dict[str, Any]) -> Signal:
    sources = contract.get("sources")
    if not isinstance(sources, list):
        return Signal(
            "Sources",
            "Missing",
            ["contract.sources is missing"],
            ["contract.sources"],
        )
    if not sources:
        return Signal(
            "Sources",
            "Missing",
            ["contract.sources is empty"],
            ["contract.sources"],
        )

    valid: list[tuple[str, str]] = []
    problems: list[str] = []
    for index, source in enumerate(sources):
        path, reason = source_value(source)
        if not path or not reason:
            problems.append(f"contract.sources[{index}] must include path and reason")
            continue
        valid.append((path, reason))

    if problems:
        return Signal("Sources", "Inconsistent", problems, ["contract.sources"])

    if any(is_placeholder_source(path) for path, _ in valid):
        return Signal(
            "Sources",
            "Weak",
            ["source evidence includes placeholder-style paths"],
            ["contract.sources"],
        )

    if len(valid) == 1:
        return Signal(
            "Sources",
            "Weak",
            ["only one source of evidence is declared"],
            ["contract.sources"],
        )

    internal_only = all(path.startswith(".ai/") or path.startswith("target/") for path, _ in valid)
    if internal_only:
        return Signal(
            "Sources",
            "Weak",
            ["sources only reference internal governance artifacts"],
            ["contract.sources"],
        )

    return Signal(
        "Sources",
        "Ready",
        [f"{len(valid)} source(s) of evidence are declared"],
        ["contract.sources"],
    )


def verification_signal(contract: dict[str, Any]) -> Signal:
    verification = contract.get("verification")
    if not isinstance(verification, list):
        return Signal(
            "Verification",
            "Missing",
            ["contract.verification is missing"],
            ["contract.verification"],
        )
    if not verification:
        return Signal(
            "Verification",
            "Missing",
            ["contract.verification is empty"],
            ["contract.verification"],
        )

    required: list[str] = []
    problems: list[str] = []
    for index, item in enumerate(verification):
        if not isinstance(item, dict):
            problems.append(f"contract.verification[{index}] must be an object")
            continue
        check = item.get("check")
        command = item.get("command")
        key = ""
        if non_empty_string(check):
            key = str(check).strip()
        elif non_empty_string(command):
            key = str(command).strip()
        else:
            problems.append(f"contract.verification[{index}] requires a check or command")
            continue
        if item.get("required") is True:
            required.append(key)

    if problems:
        return Signal("Verification", "Inconsistent", problems, ["contract.verification"])
    if not required:
        return Signal(
            "Verification",
            "Broad",
            ["verification does not declare any required checks"],
            ["contract.verification"],
        )
    return Signal(
        "Verification",
        "Ready",
        [f"verification declares {len(required)} required check(s)"],
        ["contract.verification"],
    )


def scenario_coverage_signal(contract: dict[str, Any]) -> Signal:
    risk = _dict(contract.get("riskAssessment"))
    level = risk.get("level")
    coverage = contract.get("scenarioCoverage")
    if not isinstance(coverage, list):
        if level == "low":
            return Signal(
                "Scenario Coverage",
                "Not Applicable",
                ["scenario coverage is not required for a low-risk Work Item"],
                ["contract.scenarioCoverage", "contract.riskAssessment"],
            )
        return Signal(
            "Scenario Coverage",
            "Missing",
            [f"scenario coverage is missing for {level or 'unknown'} risk"],
            ["contract.scenarioCoverage", "contract.riskAssessment"],
        )

    issues = validate_scenario_coverage(coverage)
    if issues:
        return Signal(
            "Scenario Coverage",
            "Inconsistent",
            issues,
            ["contract.scenarioCoverage", "contract.riskAssessment"],
        )

    required_items = [
        item for item in coverage if isinstance(item, dict) and item.get("required") is True
    ]
    if not required_items:
        if level == "low":
            return Signal(
                "Scenario Coverage",
                "Not Applicable",
                [
                    "scenario coverage is optional for low-risk Work Items without required scenarios"
                ],
                ["contract.scenarioCoverage", "contract.riskAssessment"],
            )
        return Signal(
            "Scenario Coverage",
            "Missing",
            ["no required scenario coverage is declared"],
            ["contract.scenarioCoverage", "contract.riskAssessment"],
        )

    statuses = {str(item.get("status")) for item in required_items}
    if "unverified" in statuses:
        return Signal(
            "Scenario Coverage",
            "Partial",
            [
                f"{len([item for item in required_items if item.get('status') == 'unverified'])} required scenario(s) remain unverified"
            ],
            ["contract.scenarioCoverage", "contract.riskAssessment"],
        )
    if statuses <= {"verified", "not_applicable"}:
        return Signal(
            "Scenario Coverage",
            "Ready",
            [f"{len(required_items)} required scenario(s) are verified or not_applicable"],
            ["contract.scenarioCoverage", "contract.riskAssessment"],
        )
    return Signal(
        "Scenario Coverage",
        "Inconsistent",
        ["scenario coverage contains unsupported required statuses"],
        ["contract.scenarioCoverage", "contract.riskAssessment"],
    )


def risk_context(contract: dict[str, Any]) -> dict[str, Any]:
    risk = _dict(contract.get("riskAssessment"))
    level = risk.get("level") if risk.get("level") in {"low", "medium", "high"} else "unknown"
    return {
        "value": level,
        "evidence": [
            f"riskAssessment.level is {level}",
            f"riskAssessment.riskTypes count: {len(_string_list(risk.get('riskTypes')))}",
        ],
        "sources": ["contract.riskAssessment"],
    }


def overall_status(signals: list[Signal], context: dict[str, Any]) -> str:
    contract = context.get("contract", {})
    if has_explicit_blocker(contract):
        return "not_ready"
    values = {signal.value for signal in signals}
    if context["scope"]["value"] in {"Missing", "Inconsistent"}:
        return "not_ready"
    if context["outOfScope"]["value"] in {"Missing", "Inconsistent"}:
        return "not_ready"
    if "Inconsistent" in values:
        return "not_ready"
    if all(value in {"Ready", "Not Applicable"} for value in values) and context["scope"][
        "value"
    ] in {"Ready", "Not Applicable"}:
        return "ready"
    return "needs_human_confirmation"


def recommendation_for(status: str, signals: list[Signal], context: dict[str, Any]) -> str:
    if status == "ready":
        return "Implementation may begin once the reviewer confirms the evidence is sufficient."
    if status == "not_ready":
        return "Resolve contradictory or missing contract evidence before implementation."

    priority = {signal.name: signal.value for signal in signals}
    if priority.get("Intent") in {"Missing", "Partial", "Inconsistent"}:
        return "Clarify intent before implementation."
    if priority.get("Scenario Coverage") in {"Missing", "Partial", "Inconsistent"}:
        return "Clarify required scenarios before implementation."
    if priority.get("Unknowns") == "Suspiciously Empty":
        return "Document the open questions that are currently implicit in the risk assessment."
    if priority.get("Sources") in {"Missing", "Weak"}:
        return "Add stronger sources before implementation."
    if priority.get("Acceptance") in {"Missing", "Broad"}:
        return "Tighten the acceptance criteria before implementation."
    if context["scope"]["value"] in {"Missing", "Broad"}:
        return "Narrow the implementation scope before implementation."
    return "Clarify the remaining evidence before implementation."


def human_decision_request(
    status: str,
    signals: list[Signal],
    *,
    contract_hash_value: str,
) -> dict[str, Any] | None:
    if status != "needs_human_confirmation":
        return None

    what_happened = [
        f"{signal.name}: {evidence}"
        for signal in signals
        if signal.value not in {"Ready", "Not Applicable"}
        for evidence in signal.evidence
    ]
    options = [
        {
            "id": "A",
            "label": "Clarify the missing decision",
            "effect": "Update the Contract before implementation.",
        },
        {
            "id": "B",
            "label": "Reduce the Work Item scope",
            "effect": "Continue only with the confirmed portion of the work.",
        },
        {
            "id": "C",
            "label": "Defer this Work Item",
            "effect": "Keep the Work Item open without implementation.",
        },
    ]
    return {
        "decisionId": f"HD-{contract_hash_value[:12]}",
        "status": status,
        "whatHappened": what_happened or ["The Contract does not determine a single safe path."],
        "whyItMatters": "Continuing would require a human decision about behavior or scope.",
        "options": options,
        "recommendedOption": "A",
        "recommendationReason": "The missing evidence should be resolved before implementation behavior is chosen.",
        "question": "Should I clarify the missing decision in the Contract before implementation?",
        "resumeCondition": "A human decision is recorded and the Preflight Review becomes ready.",
    }


def build_context(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract": contract,
        "scope": asdict(scope_signal(contract)),
        "outOfScope": asdict(out_of_scope_signal(contract)),
        "risk": risk_context(contract),
    }


def derive_report(
    contract: dict[str, Any], *, contract_path: Path, policy_path: Path
) -> dict[str, Any]:
    signals = [
        intent_signal(contract),
        unknowns_signal(contract),
        acceptance_signal(contract),
        sources_signal(contract),
        scenario_coverage_signal(contract),
        verification_signal(contract),
    ]
    context = build_context(contract)
    status = overall_status(signals, context)
    policy = load_policy(policy_path)
    current_contract_hash = contract_hash(contract_path)
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "workItemId": contract.get("workItemId", ""),
        "contractPath": contract_path.as_posix(),
        "contractHash": current_contract_hash,
        "policyPath": policy["path"],
        "policyHash": policy_hash(policy_path),
        "policyVersion": policy["version"],
        "gate": {
            "enabled": policy["gateEnabled"],
            "blockedStatuses": policy["blockedStatuses"],
        },
        "status": status,
        "signals": [asdict(signal) for signal in signals],
        "context": context,
        "decisionDrivers": decision_drivers(signals, context),
        "recommendation": recommendation_for(status, signals, context),
        "humanDecisionRequest": human_decision_request(
            status,
            signals,
            contract_hash_value=current_contract_hash,
        ),
    }
    return report


def decision_drivers(signals: list[Signal], context: dict[str, Any]) -> list[str]:
    drivers: list[str] = []
    for signal in signals:
        if signal.value not in {"Ready", "Not Applicable"}:
            drivers.extend([f"{signal.name}: {item}" for item in signal.evidence])
    for name in ("scope", "outOfScope"):
        section = context[name]
        if section["value"] not in {"Ready", "Not Applicable"}:
            drivers.extend([f"{name}: {item}" for item in section["evidence"]])
    risk = context["risk"]
    drivers.append(risk["evidence"][0])
    return drivers


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Preflight Review",
        "",
    ]
    if report.get("status") != "ready":
        lines.extend(
            [
                "Preflight Review requires attention before implementation.",
                "",
                f"Status: {report['status']}",
                "",
                f"Recommendation: {report['recommendation']}",
                "",
                "Advisory mode:",
                "This command does not block automatically.",
                "The agent must report this review to the user before coding.",
                "",
            ]
        )
    lines.extend(
        [
            "Status:",
            f"{report['status']}",
            "",
            "Signals:",
            "",
        ]
    )
    for signal in report["signals"]:
        lines.append(f"{signal['name']}:")
        lines.append(f"{signal['value']}")
        for item in signal["evidence"]:
            lines.append(f"- {item}")
        if signal["sources"]:
            lines.append(f"- Sources: {', '.join(signal['sources'])}")
        lines.append("")

    lines.extend(
        [
            "Context:",
            "",
            f"Scope: {report['context']['scope']['value']}",
        ]
    )
    for item in report["context"]["scope"]["evidence"]:
        lines.append(f"- {item}")
    lines.append(f"- Sources: {', '.join(report['context']['scope']['sources'])}")
    lines.append("")
    lines.append(f"Out of Scope: {report['context']['outOfScope']['value']}")
    for item in report["context"]["outOfScope"]["evidence"]:
        lines.append(f"- {item}")
    lines.append(f"- Sources: {', '.join(report['context']['outOfScope']['sources'])}")
    lines.append("")
    lines.append(f"Risk: {report['context']['risk']['value']}")
    for item in report["context"]["risk"]["evidence"]:
        lines.append(f"- {item}")
    lines.append(f"- Sources: {', '.join(report['context']['risk']['sources'])}")
    lines.extend(
        [
            "",
            "Recommendation:",
            "",
            report["recommendation"],
            "",
            "Decision Drivers:",
            "",
        ]
    )
    if report["decisionDrivers"]:
        lines.extend(f"- {item}" for item in report["decisionDrivers"])
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def validate_report_structure(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in (
        "generatedAt",
        "workItemId",
        "contractPath",
        "contractHash",
        "policyPath",
        "policyHash",
        "policyVersion",
        "gate",
        "status",
        "signals",
        "context",
        "decisionDrivers",
        "recommendation",
        "humanDecisionRequest",
    ):
        if field not in report:
            issues.append(f"missing field: {field}")
    if report.get("status") not in ALLOWED_STATUSES:
        issues.append(f"status must be one of {sorted(ALLOWED_STATUSES)}")
    gate = report.get("gate")
    if not isinstance(gate, dict):
        issues.append("gate must be an object")
    else:
        if not isinstance(gate.get("enabled"), bool):
            issues.append("gate.enabled must be boolean")
        blocked = gate.get("blockedStatuses")
        if not isinstance(blocked, list):
            issues.append("gate.blockedStatuses must be a list")
        elif any(item not in ALLOWED_STATUSES for item in blocked):
            issues.append(f"gate.blockedStatuses must only contain {sorted(ALLOWED_STATUSES)}")
    signals = report.get("signals")
    if not isinstance(signals, list) or not signals:
        issues.append("signals must be a non-empty list")
    else:
        for index, signal in enumerate(signals):
            if not isinstance(signal, dict):
                issues.append(f"signals[{index}] must be an object")
                continue
            if signal.get("name") not in {
                "Intent",
                "Unknowns",
                "Acceptance",
                "Sources",
                "Scenario Coverage",
                "Verification",
            }:
                issues.append(f"signals[{index}].name is invalid")
            if signal.get("value") not in ALLOWED_SIGNAL_VALUES:
                issues.append(
                    f"signals[{index}].value must be one of {sorted(ALLOWED_SIGNAL_VALUES)}"
                )
            if not isinstance(signal.get("evidence"), list) or not all(
                non_empty_string(item) for item in signal.get("evidence", [])
            ):
                issues.append(f"signals[{index}].evidence must be a list of non-empty strings")
            if not isinstance(signal.get("sources"), list) or not all(
                non_empty_string(item) for item in signal.get("sources", [])
            ):
                issues.append(f"signals[{index}].sources must be a list of non-empty strings")
    context = report.get("context")
    if not isinstance(context, dict):
        issues.append("context must be an object")
    else:
        for key in ("scope", "outOfScope", "risk"):
            section = context.get(key)
            if not isinstance(section, dict):
                issues.append(f"context.{key} must be an object")
                continue
            if section.get("value") not in ALLOWED_SIGNAL_VALUES and not (
                key == "risk" and section.get("value") in {"low", "medium", "high", "unknown"}
            ):
                issues.append(f"context.{key}.value is invalid")
            if not isinstance(section.get("evidence"), list) or not all(
                non_empty_string(item) for item in section.get("evidence", [])
            ):
                issues.append(f"context.{key}.evidence must be a list of non-empty strings")
            if not isinstance(section.get("sources"), list) or not all(
                non_empty_string(item) for item in section.get("sources", [])
            ):
                issues.append(f"context.{key}.sources must be a list of non-empty strings")
    if not isinstance(report.get("decisionDrivers"), list):
        issues.append("decisionDrivers must be a list")
    if not non_empty_string(report.get("recommendation")):
        issues.append("recommendation must be a non-empty string")
    request = report.get("humanDecisionRequest")
    if report.get("status") == "needs_human_confirmation":
        if not isinstance(request, dict):
            issues.append("humanDecisionRequest must be an object for needs_human_confirmation")
        else:
            required_request_fields = (
                "decisionId",
                "status",
                "whatHappened",
                "whyItMatters",
                "options",
                "recommendedOption",
                "recommendationReason",
                "question",
                "resumeCondition",
            )
            for field in required_request_fields:
                if field not in request:
                    issues.append(f"humanDecisionRequest missing field: {field}")
            if request.get("status") != "needs_human_confirmation":
                issues.append("humanDecisionRequest.status must be needs_human_confirmation")
            for field in ("whatHappened", "options"):
                if not isinstance(request.get(field), list) or not request.get(field):
                    issues.append(f"humanDecisionRequest.{field} must be a non-empty list")
            what_happened = request.get("whatHappened")
            if isinstance(what_happened, list) and any(
                not non_empty_string(item) for item in what_happened
            ):
                issues.append("humanDecisionRequest.whatHappened must contain non-empty strings")
            options = request.get("options")
            if isinstance(options, list):
                option_ids = set()
                for index, option in enumerate(options):
                    if not isinstance(option, dict) or set(option) != {"id", "label", "effect"}:
                        issues.append(
                            f"humanDecisionRequest.options[{index}] must contain only id, label, effect"
                        )
                        continue
                    option_ids.add(option["id"])
                    for field in ("id", "label", "effect"):
                        if not non_empty_string(option.get(field)):
                            issues.append(
                                f"humanDecisionRequest.options[{index}].{field} must be non-empty"
                            )
                if request.get("recommendedOption") not in option_ids:
                    issues.append("humanDecisionRequest.recommendedOption must reference an option")
            for field in (
                "decisionId",
                "whyItMatters",
                "recommendedOption",
                "recommendationReason",
                "question",
                "resumeCondition",
            ):
                if not non_empty_string(request.get(field)):
                    issues.append(f"humanDecisionRequest.{field} must be non-empty")
    elif request is not None:
        issues.append("humanDecisionRequest must be null unless status is needs_human_confirmation")
    return issues


def policy_issues(report: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    gate_value = report.get("gate")
    gate: dict[str, Any] = gate_value if isinstance(gate_value, dict) else {}
    if gate.get("enabled") is True and not gate.get("blockedStatuses"):
        issues.append("gate.enabled is true but blockedStatuses is empty")
    if policy["gateEnabled"] != gate.get("enabled"):
        issues.append("report gate.enabled does not match policy")
    if policy["blockedStatuses"] != gate.get("blockedStatuses"):
        issues.append("report gate.blockedStatuses does not match policy")
    if report.get("policyHash") != policy_hash(Path(policy["path"])):
        issues.append("policyHash does not match the configured policy")
    return issues


def report_is_blocked(report: dict[str, Any], policy: dict[str, Any]) -> bool:
    if not policy["gateEnabled"]:
        return False
    return report.get("status") in set(policy["blockedStatuses"])


def resolve_contract_path(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    active_dir = PROJECT_ROOT / ".ai" / "work-items" / "active"
    contracts = sorted(active_dir.glob("*.contract.json"))
    if len(contracts) == 1:
        return contracts[0]
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or validate a Preflight Review.")
    parser.add_argument("--contract")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate an existing report instead of generating one.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract_path = resolve_contract_path(args.contract)
    if contract_path is None:
        print("Skipping preflight review (no active contract provided)")
        return 0
    if not contract_path.exists():
        print(f"Failed to load preflight review contract: {contract_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    policy_path = Path(args.policy)
    try:
        contract = load_json(contract_path)
        policy = load_policy(policy_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Failed to load preflight review inputs: {exc}", file=sys.stderr)
        return 1

    if args.check:
        if not output_path.exists():
            print(f"Preflight review report is missing: {output_path}", file=sys.stderr)
            return 1
        try:
            report = load_json(output_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Failed to read preflight review report: {exc}", file=sys.stderr)
            return 1
        issues = validate_report_structure(report)
        issues.extend(policy_issues(report, policy))
        if report.get("contractHash") != contract_hash(contract_path):
            issues.append("contractHash does not match the active Contract")
        if report.get("workItemId") != contract.get("workItemId"):
            issues.append("workItemId does not match the active Contract")
        if report_is_blocked(report, policy):
            issues.append(f"preflight gate blocked status: {report.get('status')}")
        if issues:
            for issue in issues:
                print(f"[ERROR] {issue}", file=sys.stderr)
            return 1
        print(f"preflight review check passed: {output_path}")
        return 0

    report = derive_report(contract, contract_path=contract_path, policy_path=policy_path)
    issues = validate_report_structure(report)
    issues.extend(policy_issues(report, policy))
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(render_markdown(report), end="")
    print(f"preflight review generated: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
