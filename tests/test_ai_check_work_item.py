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
