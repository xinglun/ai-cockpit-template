import json
import sys
from pathlib import Path

import ai_preflight_review
import pytest


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
            "The generated report includes the ten named Preflight Review signals.",
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


def test_preflight_signals_expose_shared_protocol_envelope(tmp_path):
    contract = ready_contract()
    path = tmp_path / "task.contract.json"
    write_contract(path, contract)
    report = ai_preflight_review.derive_report(
        contract, contract_path=path, policy_path=Path("/tmp/preflight_review_policy.yaml")
    )
    signal = next(item for item in report["signals"] if item["name"] == "Capability")
    assert signal["signalId"] == "guard.capability"
    assert signal["state"] == "allow"
    assert signal["confidence"] == "deterministic"
    assert signal["safeAlternatives"] == []
    assert signal_map(report) == {
        "Raw Request": "Not Applicable",
        "Intent Capability": "Not Applicable",
        "Intent": "Ready",
        "Intent Guard": "Ready",
        "Capability": "Ready",
        "Constraint Guard": "Ready",
        "Success Criteria": "Not Applicable",
        "Unknowns": "Ready",
        "Acceptance": "Ready",
        "Sources": "Ready",
        "Scenario Coverage": "Ready",
        "Verification": "Ready",
        "Critical Domain Guard": "Ready",
        "Governance Bypass Guard": "Ready",
        "Evidence Integrity Guard": "Ready",
        "Production Operation Guard": "Ready",
    }
    summary = ai_preflight_review.presentation_summary(report)
    assert summary["status"] == "ready"
    assert summary["decision"] == "none"
    assert summary["signals"]["Intent"] == "Ready"
    assert report["context"]["scope"]["value"] == "Ready"
    assert report["context"]["outOfScope"]["value"] == "Ready"


def test_preflight_exposes_intent_and_implementation_capability_signals(tmp_path):
    contract = ready_contract()
    contract["requestedOperation"] = {
        "target": "repository_governance",
        "action": "modify",
        "environment": "repository",
        "effect": "enforce",
        "authorityRequired": False,
    }
    path = tmp_path / "task.contract.json"
    write_contract(path, contract)
    report = ai_preflight_review.derive_report(
        contract, contract_path=path, policy_path=Path("/tmp/preflight_review_policy.yaml")
    )
    signals = signal_map(report)
    assert signals["Intent Capability"] == "Ready"
    assert signals["Capability"] == "Ready"


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
    assert signal_map(report)["Intent Guard"] == "Missing"
    assert signal_map(report)["Capability"] == "Ready"
    assert signal_map(report)["Intent Capability"] == "Not Applicable"
    assert signal_map(report)["Constraint Guard"] == "Ready"
    assert signal_map(report)["Success Criteria"] == "Not Applicable"
    assert signal_map(report)["Unknowns"] == "Suspiciously Empty"
    assert signal_map(report)["Acceptance"] == "Broad"
    assert signal_map(report)["Sources"] == "Weak"
    assert signal_map(report)["Scenario Coverage"] == "Missing"
    assert signal_map(report)["Verification"] == "Missing"


def test_needs_human_confirmation_contains_structured_decision_request(tmp_path):
    contract = tmp_path / "task.contract.json"
    write_contract(contract, conservative_contract())

    report = ai_preflight_review.derive_report(
        conservative_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )

    request = report["humanDecisionRequest"]
    assert request["decisionId"].startswith("HD-")
    assert request["status"] == "needs_human_confirmation"
    assert request["whatHappened"]
    assert request["whyItMatters"]
    assert request["options"]
    assert request["recommendedOption"] in {item["id"] for item in request["options"]}
    assert request["recommendationReason"]
    assert request["question"]
    assert request["resumeCondition"]

    for option in request["options"]:
        assert set(option) == {"id", "label", "effect"}
        assert option["id"]
        assert option["label"]
        assert option["effect"]


def test_human_decision_request_validation_rejects_unknown_recommendation(tmp_path):
    contract = tmp_path / "task.contract.json"
    write_contract(contract, conservative_contract())
    report = ai_preflight_review.derive_report(
        conservative_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )
    report["humanDecisionRequest"]["recommendedOption"] = "Z"

    issues = ai_preflight_review.validate_report_structure(report)

    assert "humanDecisionRequest.recommendedOption must reference an option" in issues


def test_valid_decision_evidence_is_bound_to_current_preflight_hash(tmp_path):
    contract = tmp_path / "task.contract.json"
    write_contract(contract, conservative_contract())
    report = ai_preflight_review.derive_report(
        conservative_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )
    evidence = {
        "decisionId": report["humanDecisionRequest"]["decisionId"],
        "decision": "A",
        "workItemId": "task",
        "contractHash": report["contractHash"],
        "preflightHash": report["preflightHash"],
        "recordedAt": "2026-07-17T00:00:00+00:00",
        "recordedBy": "user",
    }
    summary = contract.with_name("task.summary.json")
    summary.write_text(json.dumps({"decisionEvidence": evidence}), encoding="utf-8")

    resumed = ai_preflight_review.derive_report(
        conservative_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )

    assert resumed["decisionState"] == "human_decision_recorded"
    assert resumed["status"] == "human_decision_recorded"
    assert resumed["decisionEvidence"] == evidence


def test_stale_or_wrong_decision_evidence_is_rejected(tmp_path):
    contract = tmp_path / "task.contract.json"
    write_contract(contract, conservative_contract())
    report = ai_preflight_review.derive_report(
        conservative_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )
    evidence = {
        "decisionId": report["humanDecisionRequest"]["decisionId"],
        "decision": "A",
        "workItemId": "wrong-task",
        "contractHash": "0" * 16,
        "preflightHash": "1" * 16,
        "recordedAt": "2026-07-17T00:00:00+00:00",
        "recordedBy": "user",
    }

    issues = ai_preflight_review.validate_decision_evidence(
        evidence,
        report,
        report["humanDecisionRequest"],
    )

    assert "decisionEvidence.workItemId does not match the current Work Item" in issues
    assert "decisionEvidence.contractHash does not match the current Contract" in issues
    assert "decisionEvidence.preflightHash does not match the current Preflight Hash" in issues


def test_gate_blocks_until_preflight_recomputes_ready(tmp_path):
    contract = tmp_path / "task.contract.json"
    write_contract(contract, conservative_contract())
    policy = tmp_path / "preflight_review_policy.yaml"
    write_policy(policy, gate_enabled=True, blocked_statuses=["needs_human_confirmation"])
    report = ai_preflight_review.derive_report(
        conservative_contract(), contract_path=contract, policy_path=policy
    )

    assert ai_preflight_review.report_is_blocked(report, ai_preflight_review.load_policy(policy))
    assert report["status"] == "needs_human_confirmation"


def test_record_decision_evidence_updates_summary_for_resume(tmp_path):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    write_contract(contract, conservative_contract())
    summary.write_text(json.dumps({"workItemId": "task"}), encoding="utf-8")
    report = ai_preflight_review.derive_report(
        conservative_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )

    evidence = ai_preflight_review.record_decision_evidence(summary, report, "A", "sei-rinn")

    stored = json.loads(summary.read_text(encoding="utf-8"))
    assert stored["decisionEvidence"] == evidence
    assert evidence["recordedBy"] == "sei-rinn"


def test_invalid_decision_evidence_is_reported_without_becoming_recorded(tmp_path):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    write_contract(contract, conservative_contract())
    summary.write_text(
        json.dumps(
            {
                "decisionEvidence": {
                    "decisionId": "HD-invalid",
                    "decision": "Z",
                    "workItemId": "task",
                    "contractHash": "0" * 16,
                    "preflightHash": "1" * 16,
                    "recordedAt": "2026-07-17T00:00:00+00:00",
                    "recordedBy": "user",
                }
            }
        ),
        encoding="utf-8",
    )

    report = ai_preflight_review.derive_report(
        conservative_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )

    assert report["decisionState"] == "invalid"
    assert report["status"] == "needs_human_confirmation"
    assert report["decisionEvidenceIssues"]


def test_record_decision_cli_requires_decision(tmp_path, monkeypatch, capsys):
    contract = tmp_path / "task.contract.json"
    write_contract(contract, conservative_contract())
    monkeypatch.setattr(
        sys,
        "argv",
        ["ai_preflight_review.py", "--contract", str(contract), "--record-decision"],
    )

    assert ai_preflight_review.main() == 2
    assert "--decision is required" in capsys.readouterr().err


def test_ready_preflight_remains_ready_after_matching_evidence_is_present(tmp_path):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    write_contract(contract, ready_contract())
    first = ai_preflight_review.derive_report(
        ready_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )
    summary.write_text(
        json.dumps(
            {
                "decisionEvidence": {
                    "decisionId": "HD-not-needed",
                    "decision": "A",
                    "workItemId": "task",
                    "contractHash": first["contractHash"],
                    "preflightHash": first["preflightHash"],
                    "recordedAt": "2026-07-17T00:00:00+00:00",
                    "recordedBy": "user",
                }
            }
        ),
        encoding="utf-8",
    )

    report = ai_preflight_review.derive_report(
        ready_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )

    assert report["status"] == "ready"
    assert report["decisionState"] == "human_decision_recorded"


def test_non_ready_preflight_request_can_be_persisted_for_protocol(tmp_path):
    import ai_decision_protocol

    contract = tmp_path / "task.contract.json"
    write_contract(contract, conservative_contract())
    report = ai_preflight_review.derive_report(
        conservative_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )
    path = ai_decision_protocol.persist_request(report, tmp_path)
    assert path is not None
    assert path.exists()


def test_decision_evidence_helpers_fail_closed_on_malformed_inputs(tmp_path):
    contract = tmp_path / "task.contract.json"
    summary = tmp_path / "task.summary.json"
    write_contract(contract, conservative_contract())
    summary.write_text("not-json", encoding="utf-8")

    assert ai_preflight_review.load_decision_evidence(contract) is None
    assert ai_preflight_review.validate_decision_evidence(None, {}, None)
    with pytest.raises(ValueError, match="only be recorded"):
        ai_preflight_review.record_decision_evidence(summary, {"status": "ready"}, "A", "user")


def test_invalid_gate_policy_boolean_is_rejected(tmp_path):
    policy = tmp_path / "policy.yaml"
    policy.write_text("gateEnabled: maybe\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid boolean"):
        ai_preflight_review.load_policy(policy)


def test_valid_report_structure_accepts_decision_protocol_fields(tmp_path):
    contract = tmp_path / "task.contract.json"
    write_contract(contract, ready_contract())
    report = ai_preflight_review.derive_report(
        ready_contract(),
        contract_path=contract,
        policy_path=Path("/tmp/preflight_review_policy.yaml"),
    )

    assert ai_preflight_review.validate_report_structure(report) == []
    assert not ai_preflight_review.report_is_blocked(
        {**report, "status": "human_decision_recorded"},
        {"gateEnabled": False, "blockedStatuses": []},
    )
    gate = {"gateEnabled": True, "blockedStatuses": ["needs_human_confirmation"]}
    assert ai_preflight_review.report_is_blocked(
        {**report, "status": "human_decision_recorded"}, gate
    )
    assert ai_preflight_review.report_is_blocked(
        {**report, "status": "needs_human_confirmation"}, gate
    )
    assert ai_preflight_review.report_is_blocked(
        {**report, "status": "not_ready", "decisionState": "invalid"}, gate
    )
    assert len(ai_preflight_review.validate_decision_evidence({}, {}, None)) >= 7
    rendered = ai_preflight_review.render_markdown(
        {**report, "decisionDrivers": [], "decisionEvidenceIssues": ["stale evidence"]}
    )
    assert "- none" in rendered
    assert "- stale evidence" in rendered


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


def test_repository_default_policy_is_fail_closed_for_all_blocked_statuses():
    policy = ai_preflight_review.load_policy(ai_preflight_review.DEFAULT_POLICY)

    assert policy["profile"] == "enforced"
    assert policy["gateEnabled"] is True
    assert policy["blockedStatuses"] == [
        "needs_human_confirmation",
        "human_decision_recorded",
        "not_ready",
    ]


def test_repository_default_policy_blocks_non_ready_preflight(tmp_path, monkeypatch):
    contract = tmp_path / "task.contract.json"
    output = tmp_path / "ai_preflight_review.json"
    write_contract(contract, conservative_contract())

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
        ],
    )

    assert ai_preflight_review.main() == 1


def test_policy_profile_is_explicit_and_validated(tmp_path):
    policy = tmp_path / "preflight_review_policy.yaml"
    write_policy(policy, gate_enabled=False, blocked_statuses=[])
    policy.write_text(
        "version: 1\nprofile: advisory\ngateEnabled: false\nblockedStatuses: []\n",
        encoding="utf-8",
    )

    assert ai_preflight_review.load_policy(policy)["profile"] == "advisory"

    policy.write_text(
        "version: 1\nprofile: unknown\ngateEnabled: false\nblockedStatuses: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid profile"):
        ai_preflight_review.load_policy(policy)


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


def test_upgrade_conflict_gate_requires_confirmation_and_accepts_it():
    report = {
        "reportVersion": 1,
        "entries": [{"path": "x", "classification": "Human Confirmation Required"}],
        "requiresHumanConfirmation": True,
    }
    assert ai_preflight_review.upgrade_conflict_gate(report, confirmed=False)
    assert ai_preflight_review.upgrade_conflict_gate(report, confirmed=True) == []


def test_partial_preflight_signal_uses_canonical_review_state():
    signal = ai_preflight_review.Signal("Intent", "Partial", ["review"], ["test"])
    assert signal.state == "review"
