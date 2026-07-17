#!/usr/bin/env python3
"""Policy-first guards for critical domains and governance bypass attempts."""

from __future__ import annotations

import re
from typing import Any


_DOMAINS = {
    "authentication": ("authentication", "login", "credential", "password", "mfa"),
    "authorization": ("authorization", "permission", "role", "privilege", "access control"),
    "payment": ("payment", "charge", "refund", "billing", "credit card"),
    "personal_data": ("personal data", "pii", "customer data", "identity data"),
    "secrets": ("secret", "api key", "token", "private key", "credential"),
    "production_release": ("production release", "deploy to prod", "publish release", "rollout"),
}
_BYPASS_TERMS = (
    "skip review",
    "bypass approval",
    "disable guard",
    "ignore policy",
    "without approval",
    "suppress check",
)
_PRODUCTION_TERMS = (
    "production operation",
    "run in production",
    "execute production",
    "live environment",
    "real-world operation",
)
_FORGERY_TERMS = (
    "forge evidence",
    "fake evidence",
    "invent approval",
    "stale approval",
    "chat approval",
)


def _text(contract: dict[str, Any]) -> str:
    intent = contract.get("intent", {})
    values = [intent.get("problem"), intent.get("rationale"), *intent.get("constraints", [])]
    return " ".join(str(item) for item in values if item).lower()


def _signal(name: str, value: str, evidence: list[str], sources: list[str]) -> dict[str, Any]:
    return {"name": name, "value": value, "evidence": evidence, "sources": sources}


def _matches(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if re.search(rf"\b{re.escape(term)}\b", text)]


def critical_domain_signal(contract: dict[str, Any]) -> dict[str, Any]:
    text = _text(contract)
    found = {domain: _matches(text, terms) for domain, terms in _DOMAINS.items()}
    found = {domain: terms for domain, terms in found.items() if terms}
    if not found:
        return _signal(
            "Critical Domain Guard",
            "Ready",
            ["no critical-domain operation is declared"],
            ["contract.intent"],
        )
    domains = ", ".join(sorted(found))
    return _signal(
        "Critical Domain Guard",
        "Inconsistent",
        [
            f"critical domain requires structured approval before implementation: {domains}",
            "safe alternative: use local fixtures, mocks, or a test environment",
        ],
        [".ai/project/capabilities.json", "contract.intent"],
    )


def governance_bypass_signal(contract: dict[str, Any]) -> dict[str, Any]:
    matches = _matches(_text(contract), _BYPASS_TERMS)
    if not matches:
        return _signal(
            "Governance Bypass Guard",
            "Ready",
            ["no governance bypass request is declared"],
            ["contract.intent"],
        )
    return _signal(
        "Governance Bypass Guard",
        "Inconsistent",
        [
            f"bypass language is forbidden: {', '.join(matches)}",
            "finish, PR, and release gates must remain enabled",
        ],
        ["contract.intent"],
    )


def evidence_forgery_signal(contract: dict[str, Any]) -> dict[str, Any]:
    matches = _matches(_text(contract), _FORGERY_TERMS)
    if not matches:
        return _signal(
            "Evidence Integrity Guard",
            "Ready",
            ["no evidence-forgery or chat-only approval request is declared"],
            ["contract.intent"],
        )
    return _signal(
        "Evidence Integrity Guard",
        "Inconsistent",
        [
            f"approval evidence cannot be fabricated: {', '.join(matches)}",
            "require identity- and hash-bound structured evidence",
        ],
        ["contract.intent", ".ai/trust/schema/human_decision_evidence.schema.json"],
    )


def production_operation_signal(contract: dict[str, Any]) -> dict[str, Any]:
    matches = _matches(_text(contract), _PRODUCTION_TERMS)
    if not matches:
        return _signal(
            "Production Operation Guard",
            "Ready",
            ["no external production operation is declared"],
            ["contract.intent"],
        )
    return _signal(
        "Production Operation Guard",
        "Inconsistent",
        [
            f"production operation is blocked: {', '.join(matches)}",
            "safe alternative: dry-run or local/test execution",
        ],
        ["contract.intent", ".ai/project/capabilities.json"],
    )


def critical_domain_signals(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        critical_domain_signal(contract),
        governance_bypass_signal(contract),
        evidence_forgery_signal(contract),
        production_operation_signal(contract),
    ]
