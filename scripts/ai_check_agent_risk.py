#!/usr/bin/env python3
"""Validate hard controls for common agent execution risks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from ai_common import PROJECT_ROOT, load_json, non_empty_string, simple_yaml_lists, verification_key
from ai_observability import create_observability, elapsed_ms


POLICY = PROJECT_ROOT / ".ai" / "guards" / "agent_risk_policy.yaml"
REPORT = PROJECT_ROOT / "target" / "ai_agent_risk_report.json"
NON_CODING_STATUSES = {"defer", "needs_human_decision", "block"}


def command_prefixes(contract: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for item in contract.get("verification", []):
        if isinstance(item, dict) and item.get("required") is True and verification_key(item):
            values.append(verification_key(item))
    return values


def has_required_gate(commands: list[str], required_prefix: str) -> bool:
    return required_prefix in commands


def matching_required_commands(commands: list[str], required_prefix: str) -> list[str]:
    return [command for command in commands if command == required_prefix]


def summary_status(summary: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(summary, dict):
        return {}
    statuses: dict[str, str] = {}
    for item in summary.get("verification", []):
        if (
            isinstance(item, dict)
            and verification_key(item)
            and isinstance(item.get("result"), str)
        ):
            statuses[verification_key(item)] = str(item["result"])
    return statuses


def checkpoint_evidence(summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(summary, dict):
        return []
    evidence = summary.get("checkpointEvidence")
    if not isinstance(evidence, list):
        return []
    return [item for item in evidence if isinstance(item, dict)]


def validate_agent_risks(
    contract: dict[str, Any], summary: dict[str, Any] | None, *, expected_contract_hash: str = ""
) -> list[str]:
    issues: list[str] = []
    policy_lists = simple_yaml_lists(POLICY)
    required_gates = policy_lists.get("risks.promptIsAdvice.requiredVerification", [])
    commands = command_prefixes(contract)
    statuses = summary_status(summary)
    for required in required_gates:
        if not has_required_gate(commands, required):
            issues.append(f"missing required AI hard gate verification: {required}")
            continue
        if isinstance(summary, dict) and required != "aiAgentRisk":
            if os.environ.get("AI_FINISH_STABILIZING") == "1" and required in {
                "aiSummary",
                "aiStatus",
                "aiStatusCheck",
            }:
                continue
            passed = [
                command
                for command in matching_required_commands(commands, required)
                if statuses.get(command) == "passed"
            ]
            if not passed:
                issues.append(f"required AI hard gate is not passed in Summary: {required}")

    decision = contract.get("executionDecision")
    decision_status = decision.get("status") if isinstance(decision, dict) else ""
    has_unknowns = isinstance(contract.get("unknowns"), list) and bool(contract.get("unknowns"))
    not_codable = contract.get("notCodable") is True
    mode = contract.get("mode")
    raw_capability = contract.get("agentCapability")
    capability: dict[str, Any] = raw_capability if isinstance(raw_capability, dict) else {}

    if mode == "code" and (has_unknowns or not_codable):
        issues.append(
            "mode code cannot proceed with unknowns or notCodable; use investigate/author_todo/review/cleanup or clear blockers"
        )
    if has_unknowns or not_codable:
        if decision_status not in NON_CODING_STATUSES:
            issues.append(
                "unknowns/notCodable require executionDecision.status to be defer, needs_human_decision, or block"
            )
        if capability.get("canImplement") is True:
            issues.append("unknowns/notCodable require agentCapability.canImplement false")
    if decision_status == "continue" and capability.get("needsHumanDecision") is True:
        issues.append(
            "executionDecision continue conflicts with agentCapability.needsHumanDecision true"
        )

    policy = contract.get("checkpointPolicy")
    if isinstance(policy, dict) and policy.get("requiredBeforeFinish") is True:
        required_stages = [
            item
            for item in policy.get("requiredStages", [])
            if isinstance(item, str) and item.strip()
        ]
        evidence_stages = {
            item.get("stage")
            for item in checkpoint_evidence(summary)
            if non_empty_string(item.get("stage")) and item.get("recorded") is True
        }
        missing = [stage for stage in required_stages if stage not in evidence_stages]
        if missing:
            issues.append(f"missing checkpointEvidence for required stage(s): {', '.join(missing)}")
        for item in checkpoint_evidence(summary):
            if item.get("stage") in required_stages and item.get("recorded") is True:
                if not non_empty_string(item.get("contractHash")):
                    issues.append(
                        f"checkpointEvidence[{item.get('stage')}].contractHash is required"
                    )
                for key in (
                    "acceptanceCount",
                    "unknownCount",
                    "requiredChecks",
                    "requiredChecksPassed",
                ):
                    if not isinstance(item.get(key), int):
                        issues.append(
                            f"checkpointEvidence[{item.get('stage')}].{key} must be integer"
                        )
                recorded_hash = item.get("contractHash")
                hashes_match = isinstance(recorded_hash, str) and (
                    recorded_hash == expected_contract_hash
                    or recorded_hash.startswith(expected_contract_hash)
                    or expected_contract_hash.startswith(recorded_hash)
                )
                if expected_contract_hash and not hashes_match:
                    issues.append(f"checkpointEvidence[{item.get('stage')}] contractHash is stale")
                expected_counts = {
                    "acceptanceCount": len(contract.get("acceptance", []))
                    if isinstance(contract.get("acceptance"), list)
                    else 0,
                    "unknownCount": len(contract.get("unknowns", []))
                    if isinstance(contract.get("unknowns"), list)
                    else 0,
                    "requiredChecks": len(commands),
                }
                for key, expected in expected_counts.items():
                    if item.get(key) != expected:
                        issues.append(f"checkpointEvidence[{item.get('stage')}].{key} is stale")

    return issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate AI agent risk controls.")
    parser.add_argument("--contract")
    parser.add_argument("--summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.contract:
        print("Skipping agent risk check (no active contract provided)")
        return 0
    start = time.time()
    try:
        contract = load_json(Path(args.contract))
        summary = (
            load_json(Path(args.summary)) if args.summary and Path(args.summary).exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Failed to run agent risk check: {exc}", file=sys.stderr)
        return 1

    expected_hash = hashlib.sha256(Path(args.contract).read_bytes()).hexdigest()[:16]
    issues = validate_agent_risks(contract, summary, expected_contract_hash=expected_hash)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {
                "status": "error" if issues else "none",
                "issues": issues,
                "contractPath": args.contract,
                "summaryPath": args.summary or "",
                "policyPath": POLICY.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    obs = create_observability(work_item_id=contract.get("workItemId", ""))
    duration = elapsed_ms(start)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        print(f"report: {REPORT.relative_to(PROJECT_ROOT)}")
        obs.check_failed(
            check_id="aiAgentRisk", duration_ms=duration, detail=f"{len(issues)} issue(s)"
        )
        return 1
    print("agent risk check passed")
    print(f"report: {REPORT.relative_to(PROJECT_ROOT)}")
    obs.check_passed(check_id="aiAgentRisk", duration_ms=duration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
