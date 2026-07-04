import ai_check_guards
import ai_check_agent_risk
import ai_check_scope
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
        "destructiveChangePolicy": {"allowed": False, "requiresHumanApproval": True, "allowPatterns": []},
        "rollbackNote": "revert",
    }


def test_destructive_allow_patterns_require_policy_and_approval():
    contract = valid_contract()
    contract["destructiveChangePolicy"]["allowPatterns"] = ["outside/**"]
    issues = ai_check_work_item.validate_contract(contract)
    assert "destructiveChangePolicy.allowPatterns require allowed true" in issues

    contract["destructiveChangePolicy"].update({"allowed": True, "approvalEvidence": {"approved": False}})
    issues = ai_check_work_item.validate_contract(contract)
    assert "destructive changes require approvalEvidence.approved true" in issues


def test_restricted_guard_is_hard_without_approval(tmp_path, monkeypatch):
    ownership = tmp_path / "ownership.yaml"
    ownership.write_text('policy/**:\n  aiWrite: restricted\n  reason: protected\n', encoding="utf-8")
    boundary = tmp_path / "boundary.yaml"
    boundary.write_text("", encoding="utf-8")
    monkeypatch.setattr(ai_check_guards, "OWNERSHIP", ownership)
    monkeypatch.setattr(ai_check_guards, "BOUNDARY", boundary)

    assert ai_check_guards.detect(["policy/rule.yaml"])[0].severity == "error"
    assert ai_check_guards.detect(["policy/rule.yaml"], restricted_approved=True)[0].severity == "warning"


def test_dependency_scope_rules_are_parsed(tmp_path):
    policy = tmp_path / "scope.yaml"
    policy.write_text('dependencyScopeRules:\n  "scripts/ai_*.py":\n    - "tests/**"\n', encoding="utf-8")
    lists = ai_check_scope.simple_yaml_lists(policy)
    assert lists["dependencyScopeRules.scripts/ai_*.py"] == ["tests/**"]


def test_adoption_bootstrap_paths_only_bypass_companion_rule_for_adoption():
    policy = {"dependencyScopeRules.scripts/ai_*.py": ["tests/**"]}
    paths = ["scripts/ai_common.py"]
    contract = {"workItemId": "adopt_ai_cockpit", "adoptionBootstrapPaths": ["scripts/ai_*.py"]}

    assert ai_check_scope.dependency_scope_issues(contract, paths, policy) == []
    assert ai_check_scope.dependency_scope_issues({}, paths, policy)


def test_adoption_bootstrap_paths_are_restricted_to_installer_work_item():
    contract = valid_contract()
    contract["adoptionBootstrapPaths"] = ["scripts/ai_*.py"]
    assert any("only allowed" in issue for issue in ai_check_work_item.validate_contract(contract))


def test_problem_statement_is_optional_but_must_not_be_empty():
    contract = valid_contract()
    contract.pop("problemStatement")
    assert "problemStatement" not in contract
    assert ai_check_work_item.validate_contract(contract) == []

    contract["problemStatement"] = ""
    issues = ai_check_work_item.validate_contract(contract)
    assert "problemStatement must be a non-empty string" in issues


def test_stale_checkpoint_hash_is_rejected():
    contract = valid_contract()
    contract["checkpointPolicy"] = {"requiredBeforeFinish": True, "requiredStages": ["before_finish"]}
    summary = {
        "checkpointEvidence": [{
            "stage": "before_finish", "recorded": True, "contractHash": "old",
            "acceptanceCount": 1, "unknownCount": 0, "requiredChecks": 1, "requiredChecksPassed": 0,
        }],
        "verification": [],
    }
    issues = ai_check_agent_risk.validate_agent_risks(contract, summary, expected_contract_hash="new")
    assert "checkpointEvidence[before_finish] contractHash is stale" in issues


def test_parse_yaml_invalid_syntax(tmp_path):
    import pytest
    from ai_common import parse_yaml
    policy = tmp_path / "invalid_yaml.yaml"

    # 1. Invalid indentation (odd number of spaces)
    policy.write_text('risks:\n   promptIsAdvice:\n     control: hard_gate', encoding="utf-8")
    with pytest.raises(ValueError, match="Indentation must be a multiple of 2 spaces"):
        parse_yaml(policy)

    # 2. Key-value without colon
    policy.write_text('risks:\n  promptIsAdvice\n    control: hard_gate', encoding="utf-8")
    with pytest.raises(ValueError, match="Expected key-value pair or key ending in"):
        parse_yaml(policy)

    # 3. Invalid list item format
    policy.write_text('risks:\n  -invalid_list_item', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid list item format"):
        parse_yaml(policy)


# ---------------------------------------------------------------------------
# intent フィールドのバリデーションテスト（V2）
# ---------------------------------------------------------------------------

def test_intent_absent_is_fully_backward_compatible():
    """intent なしの既存 Contract は引き続きパスする。"""
    contract = valid_contract()
    assert "intent" not in contract
    assert ai_check_work_item.validate_contract(contract) == []


def test_intent_empty_object_is_valid():
    """intent: {} は全フィールド任意のため合法。"""
    contract = valid_contract()
    contract["intent"] = {}
    assert ai_check_work_item.validate_contract(contract) == []


def test_intent_with_problem_only_is_valid():
    """最小構成: problem のみ記入でもパスする。"""
    contract = valid_contract()
    contract["intent"] = {"problem": "Existing contract validator silently rejects unknown schema fields."}
    assert ai_check_work_item.validate_contract(contract) == []


def test_intent_with_all_known_fields_is_valid():
    """全フィールドを記入した場合もパスする。"""
    contract = valid_contract()
    contract["intent"] = {
        "businessGoal": "Reduce scope violations in AI-assisted development.",
        "userGoal": "Agents understand why a change exists, not only what to change.",
        "problem": "Without intent context, agents often solve the wrong problem.",
        "constraints": ["Must remain backward compatible.", "No new required fields."],
        "nonGoals": ["Automatic intent generation.", "Repository memory."],
        "rationale": "Optional fields allow gradual adoption without breaking existing workflows.",
    }
    assert ai_check_work_item.validate_contract(contract) == []


def test_intent_wrong_type_is_rejected():
    """intent が object でない場合はエラー。"""
    contract = valid_contract()
    contract["intent"] = "should be an object"
    issues = ai_check_work_item.validate_contract(contract)
    assert "intent must be an object" in issues


def test_intent_unknown_key_is_rejected():
    """intent に未定義のキーが含まれる場合はエラー。"""
    contract = valid_contract()
    contract["intent"] = {"problem": "Valid problem.", "unknownKey": "not allowed"}
    issues = ai_check_work_item.validate_contract(contract)
    assert "intent.unknownKey is not a recognized field" in issues


def test_intent_string_field_empty_string_is_rejected():
    """文字列フィールドに空文字列を渡した場合はエラー。"""
    for key in ("businessGoal", "userGoal", "problem", "rationale"):
        contract = valid_contract()
        contract["intent"] = {key: ""}
        issues = ai_check_work_item.validate_contract(contract)
        assert f"intent.{key} must be a non-empty string when provided" in issues, \
            f"Expected error for empty intent.{key}"


def test_intent_list_field_wrong_type_is_rejected():
    """リストフィールドに文字列を渡した場合はエラー。"""
    for key in ("constraints", "nonGoals"):
        contract = valid_contract()
        contract["intent"] = {key: "should be a list"}
        issues = ai_check_work_item.validate_contract(contract)
        assert f"intent.{key} must be a list of non-empty strings when provided" in issues, \
            f"Expected error for non-list intent.{key}"


def test_intent_list_field_with_empty_string_item_is_rejected():
    """リストフィールドに空文字列アイテムが含まれる場合はエラー。"""
    for key in ("constraints", "nonGoals"):
        contract = valid_contract()
        contract["intent"] = {key: ["valid constraint", ""]}
        issues = ai_check_work_item.validate_contract(contract)
        assert f"intent.{key} must be a list of non-empty strings when provided" in issues, \
            f"Expected error for empty string in intent.{key}"


def test_intent_list_field_empty_list_is_valid():
    """リストフィールドに空リストを渡した場合はエラーにならない（記入なしと同等）。"""
    contract = valid_contract()
    contract["intent"] = {"constraints": [], "nonGoals": []}
    assert ai_check_work_item.validate_contract(contract) == []

