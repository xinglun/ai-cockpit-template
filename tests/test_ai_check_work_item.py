import ai_check_work_item


def valid_contract():
    return {
        "contractVersion": 1,
        "workItemId": "task",
        "mode": "code",
        "title": "Task",
        "problemStatement": "Describe the problem this task solves, or state that no product context was provided for a mechanical change.",
        "baseCommit": "1234567",
        "baselineDirtyPaths": [],
        "scope": ["scripts/**", "tests/**"],
        "outOfScope": [],
        "sources": ["spec"],
        "unknowns": [],
        "notCodable": False,
        "acceptance": ["works"],
        "verification": [{"command": "python3 -m pytest", "required": True}],
        "destructiveChangePolicy": {
            "allowed": False,
            "requiresHumanApproval": True,
            "allowPatterns": [],
        },
        "rollbackNote": "revert",
    }


def test_problem_statement_is_optional_but_must_not_be_empty():
    contract = valid_contract()
    contract.pop("problemStatement")
    assert ai_check_work_item.validate_contract(contract) == []

    contract["problemStatement"] = ""
    issues = ai_check_work_item.validate_contract(contract)
    assert "problemStatement must be a non-empty string" in issues


def test_v2_code_work_item_requires_sourced_raw_request():
    contract = valid_contract()
    contract.update(
        {
            "contractVersion": 2,
            "scope": [".ai/work-items/active/task.contract.json"],
            "baseCommit": "1234567890abcdef",
            "verification": [{"check": "quality", "required": True}],
        }
    )
    issues = ai_check_work_item.validate_contract(contract)
    assert any("rawUserRequest" in issue for issue in issues)

    contract["rawUserRequest"] = "Add a deterministic governance guard."
    contract["rawRequestSource"] = {
        "type": "human",
        "reference": "user-request:test",
        "capturedAt": "2026-07-21",
        "digest": "sha256:test",
    }
    issues = ai_check_work_item.validate_contract(contract)
    assert not any("rawUserRequest" in issue or "rawRequestSource" in issue for issue in issues)


def test_code_work_item_requires_requested_operation():
    contract = valid_contract()
    contract.update(
        {
            "contractVersion": 2,
            "scope": [".ai/work-items/active/task.contract.json"],
            "baseCommit": "1234567890abcdef",
            "verification": [{"check": "quality", "required": True}],
            "rawUserRequest": "Change governance policy.",
            "rawRequestSource": {
                "type": "human",
                "reference": "test:operation",
                "capturedAt": "2026-07-21",
                "digest": "sha256:test",
            },
            "declaredIntent": {
                "summary": "Change governance policy.",
                "requestedCapabilities": ["ai_governance"],
            },
        }
    )
    issues = ai_check_work_item.validate_contract(contract)
    assert any("requestedOperation" in issue for issue in issues)
