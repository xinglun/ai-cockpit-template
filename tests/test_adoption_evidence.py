import pytest

from ai_adoption_evidence import build_runtime_verification, validate_runtime_verification


def records():
    contract = {
        "workItemId": "adopt_ai_cockpit",
        "baseCommit": "a" * 40,
        "startReceipt": {
            "path": ".ai/work-items/starts/adopt_ai_cockpit.json",
            "baseCommit": "a" * 40,
            "initialScopeDigest": "b" * 64,
            "contractSkeletonDigest": "c" * 64,
        },
    }
    receipt = {
        "workItemId": "adopt_ai_cockpit",
        "receiptPath": ".ai/work-items/starts/adopt_ai_cockpit.json",
        "baseCommit": "a" * 40,
        "initialScopeDigest": "b" * 64,
        "contractSkeletonDigest": "c" * 64,
    }
    summary = {"workItemId": "adopt_ai_cockpit"}
    return contract, summary, receipt


def test_runtime_verification_binds_adopter_records_and_preserves_not_run():
    contract, summary, receipt = records()
    evidence = build_runtime_verification(
        contract,
        summary,
        receipt,
        source_release_tag="v2.6.0",
        source_repository="local source",
        checks=[{"check": "python", "result": "not_run", "reason": "adopter tool unavailable"}],
    )
    assert evidence["workItemId"] == "adopt_ai_cockpit"
    assert evidence["projectQualityState"] == "not_configured"
    assert evidence["checks"][0]["result"] == "not_run"
    assert validate_runtime_verification(evidence, contract, summary, receipt) == []


def test_runtime_verification_rejects_template_owned_evidence():
    contract, summary, receipt = records()
    with pytest.raises(ValueError, match="template-owned"):
        build_runtime_verification(
            contract,
            summary,
            receipt,
            source_release_tag="v2.6.0",
            source_repository="local source",
            checks=[{"check": "sbom", "result": "passed", "evidence": ".ai/cockpit/sbom.json"}],
        )


def test_runtime_verification_rejects_mismatched_receipt_binding():
    contract, summary, receipt = records()
    evidence = build_runtime_verification(
        contract,
        summary,
        receipt,
        source_release_tag="unknown",
        source_repository="local source",
        checks=[],
    )
    receipt["baseCommit"] = "d" * 40
    issues = validate_runtime_verification(evidence, contract, summary, receipt)
    assert any("receipt" in issue for issue in issues)
