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
