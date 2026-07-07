#!/usr/bin/env python3
"""Derive Cockpit governance-compression status from Contract and Summary.

The module is intentionally pure: it consumes already-loaded Contract and
Summary dictionaries and returns a structured status model without any file I/O.
Rendering helpers are kept separate so the model can be tested directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai_common import non_empty_string, verification_key


RECOMMENDATIONS = {
    "ready_for_review",
    "ready_with_risks",
    "needs_investigation",
    "blocked",
}

SIGNAL_ORDER = (
    "Intent",
    "Acceptance",
    "Unknowns",
    "Verification",
    "Guidelines",
    "Checkpoints",
    "Residual Risk",
)

VALID_SIGNAL_VALUES = {
    "Intent": {"resolved", "unresolved", "unknown", "not_applicable"},
    "Acceptance": {"complete", "incomplete", "unknown"},
    "Unknowns": {"resolved", "open", "unknown"},
    "Verification": {"passed", "failed", "incomplete"},
    "Guidelines": {"satisfied", "violated", "unknown"},
    "Checkpoints": {"complete", "incomplete", "not_required"},
    "Residual Risk": {"low", "medium", "high", "unknown"},
}

EVIDENCE_LABELS = {
    "contract": "Contract",
    "summary": "Summary",
    "verification": "Verification",
    "intentAlignment": "Intent Alignment",
    "guidelines": "Guidelines",
    "checkpoints": "Checkpoints",
    "residualRisk": "Residual Risk",
    "reviewReadiness": "Review Readiness",
}


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [item.strip() for item in values if isinstance(item, str) and item.strip()]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _summary_or_empty(summary: dict[str, Any] | None) -> dict[str, Any]:
    return summary if isinstance(summary, dict) else {}


def _has_meaningful_intent(contract: dict[str, Any]) -> bool:
    intent = contract.get("intent")
    if not isinstance(intent, dict):
        return False
    for key in ("businessGoal", "userGoal", "problem", "rationale"):
        if non_empty_string(intent.get(key)):
            return True
    for key in ("constraints", "nonGoals"):
        if _string_list(intent.get(key)):
            return True
    return False


def _required_checks(contract: dict[str, Any]) -> list[str]:
    return [
        verification_key(item)
        for item in contract.get("verification", [])
        if isinstance(item, dict) and item.get("required") is True and verification_key(item)
    ]


def _verification_index(summary: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    for item in summary.get("verification", []):
        if isinstance(item, dict):
            key = verification_key(item)
            result = item.get("result")
            if key and isinstance(result, str):
                index[key] = result
    return index


def _guidelines_index(summary: dict[str, Any]) -> dict[str, bool]:
    index: dict[str, bool] = {}
    for item in summary.get("guidelinesCompliance", []):
        if isinstance(item, dict) and non_empty_string(item.get("guideline")) and isinstance(item.get("compliant"), bool):
            index[str(item["guideline"])] = bool(item["compliant"])
    return index


def _checkpoint_stages(summary: dict[str, Any]) -> set[str]:
    stages: set[str] = set()
    for item in summary.get("checkpointEvidence", []):
        if isinstance(item, dict) and non_empty_string(item.get("stage")) and item.get("recorded") is True:
            stages.add(str(item["stage"]))
    return stages


def _max_risk_level(levels: list[str]) -> str:
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    if "low" in levels:
        return "low"
    return "unknown"


def _risk_levels(summary: dict[str, Any]) -> list[str]:
    levels: list[str] = []
    risk = summary.get("risk")
    if isinstance(risk, dict) and risk.get("level") in {"low", "medium", "high"}:
        levels.append(str(risk["level"]))
    for item in summary.get("residualRisks", []):
        if isinstance(item, dict) and item.get("level") in {"low", "medium", "high"}:
            levels.append(str(item["level"]))
    return levels


def _intent_alignment_signal(contract: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    intent = _dict(contract.get("intent"))
    if not intent:
        return {
            "value": "not_applicable",
            "evidence": ["contract.intent is absent"],
            "sources": ["contract.intent"],
        }

    meaningful = _has_meaningful_intent(contract)
    alignment = summary.get("intentAlignment")
    if not isinstance(alignment, dict) or not alignment:
        return {
            "value": "unknown" if meaningful else "not_applicable",
            "evidence": [
                "summary.intentAlignment is missing" if meaningful else "contract.intent has no meaningful content",
            ],
            "sources": ["contract.intent", "summary.intentAlignment"],
        }

    problem_present = non_empty_string(intent.get("problem"))
    constraints_present = bool(_string_list(intent.get("constraints")))
    non_goals_present = bool(_string_list(intent.get("nonGoals")))
    rationale_present = non_empty_string(intent.get("rationale"))

    problem_value = alignment.get("problemResolved")
    problem_evidence = alignment.get("problemResolutionEvidence")
    constraints_value = alignment.get("constraintsRespected")
    constraints_evidence = alignment.get("constraintsRespectEvidence")
    non_goals_value = alignment.get("nonGoalsAvoided")
    rationale_value = alignment.get("rationaleValidated")

    applicable: list[str] = []
    unresolved: list[str] = []
    unknown: list[str] = []

    def classify(field: str, present: bool, canonical_value: Any, legacy_value: Any) -> None:
        if not present:
            return
        applicable.append(field)
        if isinstance(canonical_value, bool):
            if not canonical_value:
                unresolved.append(field)
            return
        if non_empty_string(legacy_value):
            return
        elif canonical_value is None:
            unknown.append(field)
        else:
            unresolved.append(field)

    classify("problem", problem_present, problem_value, problem_evidence)
    classify("constraints", constraints_present, constraints_value, constraints_evidence)
    classify("nonGoals", non_goals_present, non_goals_value, None)
    classify("rationale", rationale_present, rationale_value if isinstance(rationale_value, str) else None, rationale_value)

    if not applicable:
        return {
            "value": "not_applicable",
            "evidence": ["contract.intent has no meaningful content"],
            "sources": ["contract.intent"],
        }

    if unresolved:
        return {
            "value": "unresolved",
            "evidence": [f"intent alignment unresolved for: {', '.join(unresolved)}"],
            "sources": ["contract.intent", "summary.intentAlignment"],
        }
    if unknown:
        return {
            "value": "unknown",
            "evidence": [f"intent alignment missing evidence for: {', '.join(unknown)}"],
            "sources": ["contract.intent", "summary.intentAlignment"],
        }

    evidence = []
    if problem_present:
        evidence.append("problem")
    if constraints_present:
        evidence.append("constraints")
    if non_goals_present:
        evidence.append("nonGoals")
    if rationale_present:
        evidence.append("rationale")
    return {
        "value": "resolved",
        "evidence": [f"intent alignment validated for: {', '.join(evidence)}"],
        "sources": ["contract.intent", "summary.intentAlignment"],
    }


def _verification_signal(contract: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    required = _required_checks(contract)
    index = _verification_index(summary)
    missing = [check for check in required if check not in index]
    failed = [check for check in required if index.get(check) == "failed"]
    not_run = [check for check in required if index.get(check) == "not_run"]
    passed = [check for check in required if index.get(check) == "passed"]

    if failed:
        value = "failed"
        evidence = [f"required verification failed: {', '.join(failed)}"]
    elif missing or not_run:
        value = "incomplete"
        detail = []
        if missing:
            detail.append(f"missing: {', '.join(missing)}")
        if not_run:
            detail.append(f"not_run: {', '.join(not_run)}")
        evidence = [f"required verification incomplete ({'; '.join(detail)})"]
    else:
        value = "passed"
        evidence = [f"required verification passed: {len(passed)}/{len(required)}"]
    return {
        "value": value,
        "evidence": evidence,
        "sources": ["contract.verification", "summary.verification"],
        "required": required,
        "passed": passed,
        "failed": failed,
        "missing": missing,
        "not_run": not_run,
    }


def _unknowns_signal(contract: dict[str, Any], summary: dict[str, Any] | None) -> dict[str, Any]:
    contract_unknowns = _string_list(contract.get("unknowns"))
    summary_unknowns = _string_list(_summary_or_empty(summary).get("unknownsRemaining"))
    if summary is None:
        return {
            "value": "unknown" if not contract_unknowns else "open",
            "evidence": ["summary is missing"],
            "sources": ["contract.unknowns", "summary.unknownsRemaining"],
        }
    if contract_unknowns or summary_unknowns:
        return {
            "value": "open",
            "evidence": [
                f"contract unknowns: {len(contract_unknowns)}",
                f"summary unknownsRemaining: {len(summary_unknowns)}",
            ],
            "sources": ["contract.unknowns", "summary.unknownsRemaining"],
        }
    return {
        "value": "resolved",
        "evidence": ["no open unknowns recorded"],
        "sources": ["contract.unknowns", "summary.unknownsRemaining"],
    }


def _acceptance_signal(contract: dict[str, Any], summary: dict[str, Any] | None, verification: dict[str, Any]) -> dict[str, Any]:
    if summary is None:
        return {
            "value": "unknown",
            "evidence": ["summary is missing"],
            "sources": ["contract.acceptance", "summary.verification", "summary.reviewReadiness"],
        }

    acceptance = contract.get("acceptance")
    if not isinstance(acceptance, list) or not acceptance:
        return {
            "value": "unknown",
            "evidence": ["contract.acceptance is missing"],
            "sources": ["contract.acceptance", "summary.verification", "summary.reviewReadiness"],
        }

    review = _dict(summary.get("reviewReadiness"))
    review_status = review.get("status")
    if review_status not in {"ready", "ready_with_risks", "not_ready", "blocked"}:
        review_status = "unknown"

    if verification["value"] != "passed":
        return {
            "value": "incomplete",
            "evidence": [f"required verification is {verification['value']}"],
            "sources": ["contract.acceptance", "summary.verification", "summary.reviewReadiness"],
        }

    if _string_list(summary.get("unknownsRemaining")):
        return {
            "value": "incomplete",
            "evidence": ["summary.unknownsRemaining is not empty"],
            "sources": ["contract.acceptance", "summary.verification", "summary.reviewReadiness"],
        }

    if review_status == "unknown":
        return {
            "value": "unknown",
            "evidence": ["summary.reviewReadiness is missing"],
            "sources": ["contract.acceptance", "summary.verification", "summary.reviewReadiness"],
        }

    if review_status in {"not_ready", "blocked"}:
        return {
            "value": "incomplete",
            "evidence": [f"reviewReadiness.status is {review_status}"],
            "sources": ["contract.acceptance", "summary.verification", "summary.reviewReadiness"],
        }

    return {
        "value": "complete",
        "evidence": [f"reviewReadiness.status is {review_status}"],
        "sources": ["contract.acceptance", "summary.verification", "summary.reviewReadiness"],
    }


def _guidelines_signal(contract: dict[str, Any], summary: dict[str, Any] | None) -> dict[str, Any]:
    guidelines = _string_list(contract.get("guidelines"))
    if not guidelines:
        return {
            "value": "satisfied",
            "evidence": ["no contract guidelines declared"],
            "sources": ["contract.guidelines", "summary.guidelinesCompliance"],
        }

    if summary is None:
        return {
            "value": "unknown",
            "evidence": ["summary is missing"],
            "sources": ["contract.guidelines", "summary.guidelinesCompliance"],
        }

    index = _guidelines_index(summary)
    missing = [item for item in guidelines if item not in index]
    violated = [item for item, compliant in index.items() if item in guidelines and compliant is False]
    if violated:
        return {
            "value": "violated",
            "evidence": [f"guideline violated: {', '.join(violated)}"],
            "sources": ["contract.guidelines", "summary.guidelinesCompliance"],
        }
    if missing:
        return {
            "value": "unknown",
            "evidence": [f"guideline compliance missing for: {', '.join(missing)}"],
            "sources": ["contract.guidelines", "summary.guidelinesCompliance"],
        }
    return {
        "value": "satisfied",
        "evidence": [f"guideline compliance satisfied for {len(guidelines)} guideline(s)"],
        "sources": ["contract.guidelines", "summary.guidelinesCompliance"],
    }


def _checkpoint_signal(contract: dict[str, Any], summary: dict[str, Any] | None) -> dict[str, Any]:
    policy = _dict(contract.get("checkpointPolicy"))
    if not policy.get("requiredBeforeFinish"):
        return {
            "value": "not_required",
            "evidence": ["checkpoint policy not required"],
            "sources": ["contract.checkpointPolicy", "summary.checkpointEvidence"],
        }

    required_stages = _string_list(policy.get("requiredStages"))
    if summary is None:
        return {
            "value": "incomplete",
            "evidence": ["summary is missing"],
            "sources": ["contract.checkpointPolicy", "summary.checkpointEvidence"],
        }

    recorded = _checkpoint_stages(summary)
    missing = [stage for stage in required_stages if stage not in recorded]
    if missing:
        return {
            "value": "incomplete",
            "evidence": [f"checkpoint evidence missing for: {', '.join(missing)}"],
            "sources": ["contract.checkpointPolicy", "summary.checkpointEvidence"],
        }
    return {
        "value": "complete",
        "evidence": [f"checkpoint evidence recorded for: {', '.join(required_stages)}"],
        "sources": ["contract.checkpointPolicy", "summary.checkpointEvidence"],
    }


def _residual_risk_signal(summary: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return {
            "value": "unknown",
            "evidence": ["summary is missing"],
            "sources": ["summary.risk", "summary.residualRisks"],
        }

    levels = _risk_levels(summary)
    if not levels:
        return {
            "value": "unknown",
            "evidence": ["no residual risk evidence recorded"],
            "sources": ["summary.risk", "summary.residualRisks"],
        }

    level = _max_risk_level(levels)
    return {
        "value": level,
        "evidence": [f"highest residual risk: {level}"],
        "sources": ["summary.risk", "summary.residualRisks"],
    }


def _review_readiness(summary: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return {
            "status": "unknown",
            "focus": [],
            "sources": ["summary.reviewReadiness"],
        }
    readiness = _dict(summary.get("reviewReadiness"))
    status = readiness.get("status")
    if status not in {"not_ready", "ready", "ready_with_risks", "blocked"}:
        status = "unknown"
    return {
        "status": status,
        "focus": _string_list(readiness.get("expectedReviewFocus")),
        "sources": ["summary.reviewReadiness"],
    }


def _destructive_change_violation(contract: dict[str, Any], summary: dict[str, Any] | None) -> bool:
    policy = _dict(contract.get("destructiveChangePolicy"))
    if policy.get("allowed") is True:
        return False
    return bool(_string_list(_summary_or_empty(summary).get("destructiveChanges")))


def derive_governance_status(contract: dict[str, Any], summary: dict[str, Any] | None) -> dict[str, Any]:
    """Return a structured, recommendation-oriented status model."""

    contract = contract if isinstance(contract, dict) else {}
    summary_dict = summary if isinstance(summary, dict) else None

    signals = {}
    signals["Intent"] = _intent_alignment_signal(contract, _summary_or_empty(summary_dict))
    verification = _verification_signal(contract, _summary_or_empty(summary_dict))
    signals["Verification"] = {
        "value": verification["value"],
        "evidence": verification["evidence"],
        "sources": verification["sources"],
    }
    signals["Unknowns"] = _unknowns_signal(contract, summary_dict)
    signals["Acceptance"] = _acceptance_signal(contract, summary_dict, verification)
    signals["Guidelines"] = _guidelines_signal(contract, summary_dict)
    signals["Checkpoints"] = _checkpoint_signal(contract, summary_dict)
    signals["Residual Risk"] = _residual_risk_signal(summary_dict)

    review = _review_readiness(summary_dict)
    decision_drivers: list[str] = []

    if contract.get("mode") == "code" and contract.get("notCodable") is True:
        decision_drivers.append("notCodable is true")
    execution_status = _dict(contract.get("executionDecision")).get("status")
    if execution_status in {"block", "blocked"}:
        decision_drivers.append(f"executionDecision is {execution_status}")
    if execution_status in {"defer", "needs_human_decision"}:
        decision_drivers.append(f"executionDecision is {execution_status}")
    if verification["value"] == "failed":
        decision_drivers.extend(verification["evidence"])
    if signals["Guidelines"]["value"] == "violated":
        decision_drivers.extend(signals["Guidelines"]["evidence"])
    if _destructive_change_violation(contract, summary_dict):
        decision_drivers.append("destructive changes are not allowed by the Contract")
    if signals["Verification"]["value"] == "incomplete":
        decision_drivers.extend(verification["evidence"])
    if signals["Unknowns"]["value"] == "open":
        decision_drivers.extend(signals["Unknowns"]["evidence"])
    if signals["Intent"]["value"] in {"unknown", "unresolved"}:
        decision_drivers.extend(signals["Intent"]["evidence"])
    if signals["Checkpoints"]["value"] == "incomplete":
        decision_drivers.extend(signals["Checkpoints"]["evidence"])
    if signals["Acceptance"]["value"] == "incomplete":
        decision_drivers.extend(signals["Acceptance"]["evidence"])
    if signals["Residual Risk"]["value"] == "unknown":
        decision_drivers.extend(signals["Residual Risk"]["evidence"])
    if review["status"] == "blocked":
        decision_drivers.append("reviewReadiness.status is blocked")
    if review["status"] == "not_ready":
        decision_drivers.append("reviewReadiness.status is not_ready")

    if any(
        reason
        for reason in decision_drivers
        if reason in {
            "notCodable is true",
            "executionDecision is block",
            "executionDecision is blocked",
            "reviewReadiness.status is blocked",
            "destructive changes are not allowed by the Contract",
        }
    ):
        recommendation = "blocked"
    elif execution_status in {"defer", "needs_human_decision"}:
        recommendation = "needs_investigation"
    elif signals["Verification"]["value"] == "failed" or signals["Guidelines"]["value"] == "violated":
        recommendation = "blocked"
    elif any(
        signal["value"] in {"incomplete", "unknown", "open"}
        for name, signal in signals.items()
        if name in {"Acceptance", "Unknowns", "Verification", "Checkpoints", "Residual Risk", "Intent"}
    ) or review["status"] in {"unknown", "not_ready"}:
        recommendation = "needs_investigation"
    else:
        residual = signals["Residual Risk"]["value"]
        if residual in {"medium", "high"} or review["status"] == "ready_with_risks":
            recommendation = "ready_with_risks"
        else:
            recommendation = "ready_for_review"

    if recommendation not in RECOMMENDATIONS:
        recommendation = "needs_investigation"

    # Keep the evidence compact and explainable.
    contract_evidence = [
        f"intent={'present' if _has_meaningful_intent(contract) else 'absent'}",
        f"acceptance={len(_string_list(contract.get('acceptance')))}",
        f"unknowns={len(_string_list(contract.get('unknowns')))}",
        f"guidelines={len(_string_list(contract.get('guidelines')))}",
        f"checkpointPolicy={'required' if _dict(contract.get('checkpointPolicy')).get('requiredBeforeFinish') else 'not_required'}",
    ]
    summary_evidence = [
        f"verification={len(verification['passed'])}/{len(verification['required'])} passed",
        f"unknownsRemaining={len(_string_list(_summary_or_empty(summary_dict).get('unknownsRemaining')))}",
        f"reviewReadiness={review['status']}",
        f"residualRisk={signals['Residual Risk']['value']}",
    ]
    verification_index = _verification_index(_summary_or_empty(summary_dict))
    verification_evidence = [f"{check}: {verification_index.get(check, verification['value'])}" for check in verification["required"]]
    intent_alignment_evidence = signals["Intent"]["evidence"]
    checkpoint_evidence = signals["Checkpoints"]["evidence"]
    guideline_evidence = signals["Guidelines"]["evidence"]
    risk_evidence = signals["Residual Risk"]["evidence"]

    return {
        "recommendation": recommendation,
        "signals": [
            {"name": name, "value": signals[name]["value"], "sources": signals[name]["sources"]}
            for name in SIGNAL_ORDER
        ],
        "evidence": {
            "contract": contract_evidence,
            "summary": summary_evidence,
            "verification": verification_evidence,
            "intentAlignment": intent_alignment_evidence,
            "guidelines": guideline_evidence,
            "checkpoints": checkpoint_evidence,
            "residualRisk": risk_evidence,
            "reviewReadiness": [f"status={review['status']}"] + ([f"focus={', '.join(review['focus'])}"] if review["focus"] else []),
        },
        "decisionDrivers": decision_drivers,
        "reviewReadiness": review,
        "sources": {
            "contract": ["contract.intent", "contract.acceptance", "contract.unknowns", "contract.guidelines", "contract.checkpointPolicy"],
            "summary": ["summary.intentAlignment", "summary.verification", "summary.unknownsRemaining", "summary.guidelinesCompliance", "summary.checkpointEvidence", "summary.risk", "summary.residualRisks", "summary.reviewReadiness"],
        },
    }


def render_active_status(
    model: dict[str, Any],
    *,
    work_item_id: str,
    mode: str,
    contract_path: str,
    summary_path: str,
    generated_at: str | None = None,
    backtrack_report: str | None = None,
    backtrack_status: str | None = None,
    backtrack_items: list[dict[str, Any]] | None = None,
) -> str:
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        "title: AI Cockpit Current Status",
        "generated: true",
        "---",
        "",
        "# AI Cockpit Current Status",
        "",
        "This file is generated by `scripts/ai_generate_status.py`. Do not update it by hand.",
        "",
        f"- Generated At: `{timestamp}`",
        f"- Task: `{work_item_id}`",
        f"- Mode: `{mode}`",
        f"- State: `{model['recommendation']}`",
        f"- Recommendation: `{model['recommendation']}`",
        f"- Contract Path: `{contract_path}`",
        f"- Summary Path: `{summary_path}`",
        "",
        "## Governance Signals",
        "",
    ]
    for signal in model["signals"]:
        lines.append(f"- {signal['name']}: {signal['value']}")

    lines.extend(["", "## Evidence", ""])
    for key in ("contract", "summary", "verification", "intentAlignment", "guidelines", "checkpoints", "residualRisk", "reviewReadiness"):
        entries = model["evidence"].get(key, [])
        if not entries:
            lines.append(f"- {EVIDENCE_LABELS.get(key, key)}: none")
            continue
        if len(entries) == 1:
            lines.append(f"- {EVIDENCE_LABELS.get(key, key)}: `{entries[0]}`")
        else:
            lines.append(f"- {EVIDENCE_LABELS.get(key, key)}: `{'; '.join(entries)}`")

    lines.extend(["", "## Decision Drivers", ""])
    if model["decisionDrivers"]:
        lines.extend(f"- {driver}" for driver in model["decisionDrivers"])
    else:
        lines.append("- none")

    lines.extend(["", "## Backtrack", ""])
    if backtrack_status:
        lines.append(f"- Status: `{backtrack_status}`")
    elif backtrack_report:
        lines.append("- Status: `unknown`")
    else:
        lines.append("- Status: `not_run`")
    if backtrack_report:
        lines.append(f"- Report: `{backtrack_report}`")
    if backtrack_items:
        for item in backtrack_items:
            if isinstance(item, dict):
                lines.append(f"- {item.get('kind')}: `{item.get('path')}` - {item.get('detail')}")
    elif backtrack_report:
        lines.append("- Items: none")

    lines.extend(["", "## Next Action", "", "- human review / commit decision"])
    return "\n".join(lines) + "\n"
