import json

import ai_check_summary
import ai_finish
from ai_common import PROJECT_ROOT


ARCHIVE_SUMMARY = (
    PROJECT_ROOT / ".ai" / "work-items" / "archive" / "2026" / "realign_ai_cockpit_v2.summary.json"
)


def test_summary_validator_orchestrates_focused_validation_helpers(monkeypatch):
    monkeypatch.setattr(
        ai_check_summary,
        "_validate_summary_structure",
        lambda *_args, **_kwargs: ["structure"],
    )
    monkeypatch.setattr(
        ai_check_summary,
        "_validate_verification_entries",
        lambda *_args, **_kwargs: ["verification"],
    )
    monkeypatch.setattr(
        ai_check_summary,
        "_validate_summary_metadata",
        lambda *_args, **_kwargs: ["metadata"],
    )
    monkeypatch.setattr(
        ai_check_summary,
        "_validate_required_verification",
        lambda *_args, **_kwargs: ["required"],
    )

    assert ai_check_summary.validate_summary({}, None) == [
        "structure",
        "verification",
        "metadata",
        "required",
    ]


def test_passed_v2_evidence_requires_worktree_digest():
    item = ai_finish.evidence(
        "projectTest",
        "make ai-cockpit-project-test",
        0,
        1,
        "passed\n",
        contract_hash="b" * 64,
        commit_sha="a" * 40,
        execution_contract_path=".ai/work-items/active/task.contract.json",
        execution_summary_path=".ai/work-items/active/task.summary.json",
        worktree_digest="c" * 64,
    )
    item.pop("worktreeDigest")
    summary = {
        "summaryVersion": 2,
        "workItemId": "task",
        "contractPath": ".ai/work-items/active/task.contract.json",
        "changedFiles": [{"path": "scripts/ai_check_summary.py", "reason": "fixture"}],
        "verification": [item],
        "risk": {"level": "low", "detail": "fixture"},
    }
    issues = ai_check_summary.validate_summary(
        summary,
        {
            "contractVersion": 2,
            "workItemId": "task",
            "verification": [{"check": "projectTest", "required": True}],
        },
    )
    assert "verification[0].worktreeDigest is required for passed result" in issues


def test_legacy_archive_summary_without_v2_fields_remains_readable():
    item = ai_finish.evidence(
        "projectTest",
        "make ai-cockpit-project-test",
        0,
        1,
        "passed\n",
        contract_hash="b" * 64,
        commit_sha="a" * 40,
        execution_contract_path=".ai/work-items/archive/2026/task.contract.json",
        execution_summary_path=".ai/work-items/archive/2026/task.summary.json",
        worktree_digest="c" * 64,
    )
    item.pop("worktreeDigest")
    summary = {
        "workItemId": "task",
        "contractPath": ".ai/work-items/archive/2026/task.contract.json",
        "changedFiles": [{"path": "scripts/ai_check_summary.py", "reason": "fixture"}],
        "sourcesUsed": ["fixture"],
        "verification": [item],
        "unknownsRemaining": [],
        "risk": {"level": "low", "detail": "fixture"},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
    }
    issues = ai_check_summary.validate_summary(
        summary,
        {"contractVersion": 2, "workItemId": "task"},
        legacy_archive=True,
    )
    assert issues == []


def test_intent_alignment_validator_accepts_empty_and_partial_payloads():
    assert ai_check_summary.validate_intent_alignment({"intentAlignment": {}}) == []
    assert ai_check_summary.validate_intent_alignment({"intentAlignment": None}) == []
    assert (
        ai_check_summary.validate_intent_alignment({"intentAlignment": {"problemResolved": True}})
        == []
    )
    assert (
        ai_check_summary.validate_intent_alignment(
            {"intentAlignment": {"problemResolutionEvidence": "legacy evidence text"}}
        )
        == []
    )
    assert (
        ai_check_summary.validate_intent_alignment(
            {"intentAlignment": {"constraintsRespectEvidence": "legacy evidence text"}}
        )
        == []
    )


def test_intent_alignment_validator_accepts_legacy_archive_payload():
    archive_summary = json.loads(ARCHIVE_SUMMARY.read_text(encoding="utf-8"))
    assert (
        ai_check_summary.validate_intent_alignment(
            {"intentAlignment": archive_summary["intentAlignment"]}
        )
        == []
    )


def test_intent_alignment_validator_rejects_unknown_keys():
    issues = ai_check_summary.validate_intent_alignment(
        {"intentAlignment": {"problemResolved": True, "unknownKey": False}}
    )
    assert "intentAlignment.unknownKey is not a recognized field" in issues


def test_scenario_coverage_validator_accepts_valid_payload():
    summary = {
        "summaryVersion": 2,
        "workItemId": "task",
        "contractPath": ".ai/work-items/active/task.contract.json",
        "changedFiles": [{"path": "src/app.py", "reason": "fixture"}],
        "sourcesUsed": ["spec"],
        "scenarioCoverage": [
            {
                "scenario": "example verified scenario",
                "required": True,
                "status": "verified",
                "evidence": ["make example-check"],
            },
            {
                "scenario": "example unverified scenario",
                "required": True,
                "status": "unverified",
                "evidence": [],
                "reason": "Waiting on an external run.",
            },
            {
                "scenario": "example not applicable scenario",
                "required": False,
                "status": "not_applicable",
                "evidence": [],
                "reason": "Legacy path not touched.",
            },
        ],
        "verification": [{"check": "quality", "result": "not_run"}],
        "unknownsRemaining": [],
        "risk": {"level": "low", "detail": "fixture"},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
        "reviewReadiness": {"status": "ready", "reason": "fixture", "expectedReviewFocus": []},
        "boundaryChecks": {
            "runtimeEntrypoints": "not_applicable",
            "userVisibleOutput": "not_applicable",
            "persistence": "not_applicable",
            "localization": "not_applicable",
            "generatedArtifacts": "not_applicable",
            "makeEntrypoints": "not_applicable",
        },
        "knownGaps": [],
        "overclaimPrevention": "fixture",
    }

    assert (
        ai_check_summary.validate_summary(summary, {"workItemId": "task", "contractVersion": 2})
        == []
    )


def test_scenario_coverage_validator_rejects_invalid_required_entries():
    summary = {
        "summaryVersion": 2,
        "workItemId": "task",
        "contractPath": ".ai/work-items/active/task.contract.json",
        "changedFiles": [{"path": "src/app.py", "reason": "fixture"}],
        "sourcesUsed": ["spec"],
        "scenarioCoverage": [
            {
                "scenario": "example verified scenario",
                "required": True,
                "status": "verified",
                "evidence": [],
            },
            {
                "scenario": "example not applicable scenario",
                "required": True,
                "status": "not_applicable",
                "evidence": [],
            },
        ],
        "verification": [{"check": "quality", "result": "not_run"}],
        "unknownsRemaining": [],
        "risk": {"level": "low", "detail": "fixture"},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
        "reviewReadiness": {"status": "ready", "reason": "fixture", "expectedReviewFocus": []},
        "boundaryChecks": {
            "runtimeEntrypoints": "not_applicable",
            "userVisibleOutput": "not_applicable",
            "persistence": "not_applicable",
            "localization": "not_applicable",
            "generatedArtifacts": "not_applicable",
            "makeEntrypoints": "not_applicable",
        },
        "knownGaps": [],
        "overclaimPrevention": "fixture",
    }

    issues = ai_check_summary.validate_summary(
        summary, {"workItemId": "task", "contractVersion": 2}
    )
    assert (
        "scenarioCoverage[0].evidence must contain at least one item when status is verified"
        in issues
    )
    assert "scenarioCoverage[1].reason is required when status is not_applicable" in issues


def test_summary_validator_rejects_summary_filename_mismatch():
    summary = {
        "summaryVersion": 2,
        "workItemId": "wrong",
        "contractPath": ".ai/work-items/active/task.contract.json",
        "changedFiles": [{"path": "scripts/app.py", "reason": "changed"}],
        "sourcesUsed": ["spec"],
        "verification": [{"check": "quality", "result": "passed"}],
        "unknownsRemaining": [],
        "risk": {"level": "low", "detail": "fixture"},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
    }

    issues = ai_check_summary.validate_summary(
        summary,
        {
            "contractVersion": 2,
            "workItemId": "wrong",
            "verification": [{"check": "quality", "required": True}],
        },
        summary_path=".ai/work-items/active/right.summary.json",
    )

    assert "workItemId does not match the Summary filename" in issues


def test_summary_validator_rejects_contract_path_mismatch():
    summary = {
        "summaryVersion": 2,
        "workItemId": "task",
        "contractPath": ".ai/work-items/archive/2026/task.contract.json",
        "changedFiles": [{"path": "scripts/app.py", "reason": "changed"}],
        "sourcesUsed": ["spec"],
        "verification": [{"check": "quality", "result": "passed"}],
        "unknownsRemaining": [],
        "risk": {"level": "low", "detail": "fixture"},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
    }

    issues = ai_check_summary.validate_summary(
        summary,
        {
            "contractVersion": 2,
            "workItemId": "task",
            "verification": [{"check": "quality", "required": True}],
        },
        contract_path=".ai/work-items/active/task.contract.json",
        summary_path=".ai/work-items/active/task.summary.json",
    )

    assert "contractPath does not match the Contract path" in issues


def test_summary_validator_rejects_unknown_active_fields():
    summary = {
        "summaryVersion": 2,
        "workItemId": "task",
        "contractPath": ".ai/work-items/active/task.contract.json",
        "changedFiles": [{"path": "scripts/app.py", "reason": "changed"}],
        "sourcesUsed": ["spec"],
        "verification": [{"check": "quality", "result": "passed"}],
        "unknownsRemaining": [],
        "risk": {"level": "low", "detail": "fixture"},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
    }
    summary["unexpectedField"] = True

    issues = ai_check_summary.validate_summary(
        summary,
        {
            "contractVersion": 2,
            "workItemId": "task",
            "verification": [{"check": "quality", "required": True}],
        },
        summary_path=".ai/work-items/active/task.summary.json",
    )

    assert "unknown field: unexpectedField" in issues


def test_summary_validator_accepts_positive_archive_sequence_and_rejects_invalid_value():
    summary = {
        "summaryVersion": 2,
        "workItemId": "task",
        "contractPath": ".ai/work-items/archive/2026/task.contract.json",
        "changedFiles": [{"path": "scripts/app.py", "reason": "changed"}],
        "sourcesUsed": ["spec"],
        "verification": [{"check": "quality", "result": "not_run"}],
        "unknownsRemaining": [],
        "risk": {"level": "low", "detail": "fixture"},
        "generatedFiles": [],
        "destructiveChanges": [],
        "observedIssues": [],
        "archiveSequence": 3,
    }
    contract = {"contractVersion": 2, "workItemId": "task", "verification": []}

    assert ai_check_summary.validate_summary(summary, contract, legacy_archive=True) == []
    summary["archiveSequence"] = 0
    issues = ai_check_summary.validate_summary(summary, contract, legacy_archive=True)
    assert "archiveSequence must be a positive integer when present" in issues
