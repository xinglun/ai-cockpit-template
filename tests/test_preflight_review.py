import json
import sys
from pathlib import Path

import ai_preflight_review


def write_contract(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def write_policy(path: Path, *, gate_enabled: bool, blocked_statuses: list[str]) -> None:
    lines = [
        "# Preflight Review policy.",
        "version: 1",
        f"gateEnabled: {'true' if gate_enabled else 'false'}",
        "blockedStatuses:",
    ]
    lines.extend(f"  - {item}" for item in blocked_statuses)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ready_contract() -> dict:
    return {
        "workItemId": "task",
        "mode": "code",
        "scope": ["scripts/**"],
        "outOfScope": ["docs/**"],
        "intent": {
            "problem": "Add a derived readiness view for active Work Items.",
            "constraints": ["Keep the derivation generic."],
            "rationale": "A contract-derived view is more explainable than self-declared readiness.",
        },
        "unknowns": [],
        "acceptance": [
            "The generated report includes the six named Preflight Review signals.",
            "The report can be generated and validated with the new Make targets.",
        ],
        "sources": [
            {"path": "docs/design.md", "reason": "Explains the readiness requirement."},
            {"path": "docs/spec.md", "reason": "Defines the contract evidence inputs."},
        ],
        "scenarioCoverage": [
            {
                "scenario": "implementation-ready path",
                "required": True,
                "status": "verified",
                "evidence": ["make test"],
            }
        ],
        "verification": [{"check": "quality", "required": True}],
        "riskAssessment": {"level": "low", "riskTypes": [], "reason": "fixture"},
    }


def conservative_contract() -> dict:
    return {
        "workItemId": "task",
        "mode": "code",
        "scope": ["scripts/**"],
        "outOfScope": ["docs/**"],
        "unknowns": [],
        "acceptance": ["Implement the feature."],
        "sources": [{"path": "docs/spec.md", "reason": "Single source of evidence."}],
        "verification": [],
        "riskAssessment": {
            "level": "medium",
            "riskTypes": ["governance_change"],
            "reason": "fixture",
        },
    }


def signal_map(report: dict) -> dict[str, str]:
    return {item["name"]: item["value"] for item in report["signals"]}


def test_ready_contract_derives_ready_preflight_review(tmp_path):
    contract = tmp_path / "task.contract.json"
    write_contract(contract, ready_contract())
    report = ai_preflight_review.derive_report(
        ready_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )

    assert report["status"] == "ready"
    assert signal_map(report) == {
        "Intent": "Ready",
        "Unknowns": "Ready",
        "Acceptance": "Ready",
        "Sources": "Ready",
        "Scenario Coverage": "Ready",
        "Verification": "Ready",
    }
    assert report["context"]["scope"]["value"] == "Ready"
    assert report["context"]["outOfScope"]["value"] == "Ready"


def test_conservative_contract_stays_advisory(tmp_path):
    contract = tmp_path / "task.contract.json"
    write_contract(contract, conservative_contract())
    report = ai_preflight_review.derive_report(
        conservative_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )

    assert report["status"] == "needs_human_confirmation"
    assert signal_map(report)["Intent"] == "Missing"
    assert signal_map(report)["Unknowns"] == "Suspiciously Empty"
    assert signal_map(report)["Acceptance"] == "Broad"
    assert signal_map(report)["Sources"] == "Weak"
    assert signal_map(report)["Scenario Coverage"] == "Missing"
    assert signal_map(report)["Verification"] == "Missing"


def test_main_prints_pause_banner_for_non_ready_status(tmp_path, monkeypatch, capsys):
    contract = tmp_path / "task.contract.json"
    output = tmp_path / "ai_preflight_review.json"
    policy = tmp_path / "preflight_review_policy.yaml"
    write_contract(contract, conservative_contract())
    write_policy(policy, gate_enabled=False, blocked_statuses=[])

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_preflight_review.py",
            "--contract",
            str(contract),
            "--output",
            str(output),
            "--policy",
            str(policy),
        ],
    )

    assert ai_preflight_review.main() == 0
    text = capsys.readouterr().out
    assert "Preflight Review requires attention before implementation." in text
    assert "Advisory mode:" in text
    assert "The agent must report this review to the user before coding." in text
    assert not (tmp_path / "ai_preflight_review.md").exists()


def test_check_only_fails_when_policy_enables_gate(tmp_path, monkeypatch):
    contract = tmp_path / "task.contract.json"
    output = tmp_path / "ai_preflight_review.json"
    policy = tmp_path / "preflight_review_policy.yaml"
    write_contract(contract, conservative_contract())
    write_policy(policy, gate_enabled=True, blocked_statuses=["needs_human_confirmation"])

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_preflight_review.py",
            "--contract",
            str(contract),
            "--output",
            str(output),
            "--policy",
            str(policy),
        ],
    )
    assert ai_preflight_review.main() == 0

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_preflight_review.py",
            "--check",
            "--contract",
            str(contract),
            "--output",
            str(output),
            "--policy",
            str(policy),
        ],
    )
    assert ai_preflight_review.main() == 1


def test_check_passes_when_policy_is_advisory_only(tmp_path, monkeypatch):
    contract = tmp_path / "task.contract.json"
    output = tmp_path / "ai_preflight_review.json"
    policy = tmp_path / "preflight_review_policy.yaml"
    write_contract(contract, ready_contract())
    write_policy(policy, gate_enabled=False, blocked_statuses=[])

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_preflight_review.py",
            "--contract",
            str(contract),
            "--output",
            str(output),
            "--policy",
            str(policy),
        ],
    )
    assert ai_preflight_review.main() == 0

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_preflight_review.py",
            "--check",
            "--contract",
            str(contract),
            "--output",
            str(output),
            "--policy",
            str(policy),
        ],
    )
    assert ai_preflight_review.main() == 0


def test_preflight_signal_helpers_cover_boundary_states():
    contract = ready_contract()
    contract["scope"] = []
    contract["outOfScope"] = []
    assert ai_preflight_review.scope_signal(contract).value == "Missing"
    assert ai_preflight_review.out_of_scope_signal(contract).value == "Not Applicable"
    assert (
        ai_preflight_review.overall_status(
            [], {"contract": {"notCodable": True}, "scope": {"value": "Missing"}}
        )
        == "not_ready"
    )


def test_preflight_signals_cover_missing_overlap_broad_and_partial_states():
    assert ai_preflight_review.scope_signal({}).value == "Missing"
    assert (
        ai_preflight_review.scope_signal({"scope": ["src/**"], "outOfScope": ["src/**"]}).value
        == "Inconsistent"
    )
    assert ai_preflight_review.scope_signal({"scope": ["**"], "outOfScope": []}).value == "Broad"
    assert ai_preflight_review.out_of_scope_signal({}).value == "Missing"
    assert ai_preflight_review.out_of_scope_signal({"outOfScope": [""]}).value == "Inconsistent"
    assert (
        ai_preflight_review.intent_signal(
            {"intent": {"problem": "p", "constraints": [], "rationale": None}}
        ).value
        == "Partial"
    )
    assert (
        ai_preflight_review.unknowns_signal(
            {"unknowns": [], "riskAssessment": {"level": "low"}}
        ).value
        == "Ready"
    )
    assert (
        ai_preflight_review.acceptance_signal(
            {
                "acceptance": [
                    "done",
                    "specific concrete acceptance condition with measurable evidence",
                ]
            }
        ).value
        == "Partial"
    )


def test_preflight_sources_verification_and_scenario_boundaries():
    assert ai_preflight_review.sources_signal({}).value == "Missing"
    assert ai_preflight_review.sources_signal({"sources": ["only"]}).value == "Inconsistent"
    assert (
        ai_preflight_review.sources_signal(
            {"sources": [{"path": "docs/spec.md", "reason": "evidence"}]}
        ).value
        == "Weak"
    )
    assert (
        ai_preflight_review.sources_signal(
            {
                "sources": [
                    {"path": "docs/spec.md", "reason": "evidence"},
                    {"path": "src/app.py", "reason": "implementation"},
                ]
            }
        ).value
        == "Ready"
    )
    assert ai_preflight_review.verification_signal({}).value == "Missing"
    assert ai_preflight_review.verification_signal({"verification": []}).value == "Missing"
    assert (
        ai_preflight_review.verification_signal({"verification": [{"command": "make test"}]}).value
        == "Broad"
    )
    assert (
        ai_preflight_review.scenario_coverage_signal({"riskAssessment": {"level": "low"}}).value
        == "Not Applicable"
    )
