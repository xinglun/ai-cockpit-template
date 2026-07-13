import json
import sys
import ai_check_guidelines


# ガイドラインチェックのユニットテスト。
# 指針（Guidelines）の検証結果（Summary）との整合性をアサーションで検査します。修正（テスト用追加修正）。
def test_guidelines_check_pass(tmp_path, monkeypatch):
    contract_file = tmp_path / "task.contract.json"
    summary_file = tmp_path / "task.summary.json"

    contract_data = {"workItemId": "task", "guidelines": ["Guideline 1", "Guideline 2"]}
    summary_data = {
        "workItemId": "task",
        "guidelinesCompliance": [
            {"guideline": "Guideline 1", "compliant": True, "evidence": "Verified G1"},
            {"guideline": "Guideline 2", "compliant": True, "evidence": "Verified G2"},
        ],
    }

    contract_file.write_text(json.dumps(contract_data), encoding="utf-8")
    summary_file.write_text(json.dumps(summary_data), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_check_guidelines.py",
            "--contract",
            str(contract_file),
            "--summary",
            str(summary_file),
        ],
    )
    assert ai_check_guidelines.main() == 0


def test_guidelines_check_missing_compliance(tmp_path, monkeypatch, capsys):
    contract_file = tmp_path / "task.contract.json"
    summary_file = tmp_path / "task.summary.json"

    contract_data = {"workItemId": "task", "guidelines": ["Guideline 1", "Guideline 2"]}
    summary_data = {
        "workItemId": "task",
        "guidelinesCompliance": [
            {"guideline": "Guideline 1", "compliant": True, "evidence": "Verified G1"}
        ],
    }

    contract_file.write_text(json.dumps(contract_data), encoding="utf-8")
    summary_file.write_text(json.dumps(summary_data), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_check_guidelines.py",
            "--contract",
            str(contract_file),
            "--summary",
            str(summary_file),
        ],
    )
    assert ai_check_guidelines.main() == 1
    captured = capsys.readouterr()
    assert "Missing compliance details in Summary for guideline" in captured.err


def test_guidelines_check_not_compliant(tmp_path, monkeypatch, capsys):
    contract_file = tmp_path / "task.contract.json"
    summary_file = tmp_path / "task.summary.json"

    contract_data = {"workItemId": "task", "guidelines": ["Guideline 1"]}
    summary_data = {
        "workItemId": "task",
        "guidelinesCompliance": [
            {"guideline": "Guideline 1", "compliant": False, "evidence": "Tried but failed"}
        ],
    }

    contract_file.write_text(json.dumps(contract_data), encoding="utf-8")
    summary_file.write_text(json.dumps(summary_data), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_check_guidelines.py",
            "--contract",
            str(contract_file),
            "--summary",
            str(summary_file),
        ],
    )
    assert ai_check_guidelines.main() == 1
    captured = capsys.readouterr()
    assert "Guideline compliance not confirmed" in captured.err


def test_guidelines_check_missing_evidence(tmp_path, monkeypatch, capsys):
    contract_file = tmp_path / "task.contract.json"
    summary_file = tmp_path / "task.summary.json"

    contract_data = {"workItemId": "task", "guidelines": ["Guideline 1"]}
    summary_data = {
        "workItemId": "task",
        "guidelinesCompliance": [{"guideline": "Guideline 1", "compliant": True, "evidence": ""}],
    }

    contract_file.write_text(json.dumps(contract_data), encoding="utf-8")
    summary_file.write_text(json.dumps(summary_data), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ai_check_guidelines.py",
            "--contract",
            str(contract_file),
            "--summary",
            str(summary_file),
        ],
    )
    assert ai_check_guidelines.main() == 1
    captured = capsys.readouterr()
    assert "Empty compliance evidence for guideline" in captured.err
