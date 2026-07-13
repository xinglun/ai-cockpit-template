"""ai_checkpoint.intent_context() のユニットテスト。"""

import ai_checkpoint


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _contract_with_intent(intent):
    """intent フィールドを持つ最小 Contract を返す。"""
    return {"intent": intent}


def _contract_without_intent():
    """intent フィールドを持たない Contract を返す。"""
    return {"workItemId": "task"}


def _missing_intent_lines():
    return [
        "problem: not provided",
        "constraint: not provided",
        "rationale: not provided",
    ]


# ---------------------------------------------------------------------------
# intent セクション自体が欠落・不正な場合
# ---------------------------------------------------------------------------


def test_intent_absent_returns_empty():
    """intent フィールドがない Contract は既定の未提供表示を返す。"""
    assert ai_checkpoint.intent_context(_contract_without_intent()) == _missing_intent_lines()


def test_intent_not_dict_returns_empty():
    """intent が dict 以外（文字列など）の場合は既定表示を返す。"""
    assert ai_checkpoint.intent_context(_contract_with_intent("invalid")) == _missing_intent_lines()


def test_intent_empty_dict_returns_empty():
    """intent: {} は表示する内容がないため既定表示を返す。"""
    assert ai_checkpoint.intent_context(_contract_with_intent({})) == _missing_intent_lines()


# ---------------------------------------------------------------------------
# None・空文字列のスキップ
# ---------------------------------------------------------------------------


def test_problem_none_is_skipped():
    """intent.problem が None の場合は not provided が表示される。"""
    result = ai_checkpoint.intent_context(_contract_with_intent({"problem": None}))
    assert result == _missing_intent_lines()


def test_problem_empty_string_is_skipped():
    """intent.problem が空文字列の場合は not provided が表示される。"""
    result = ai_checkpoint.intent_context(_contract_with_intent({"problem": ""}))
    assert result == _missing_intent_lines()


def test_problem_whitespace_only_is_skipped():
    """intent.problem が空白のみの場合は not provided が表示される。"""
    result = ai_checkpoint.intent_context(_contract_with_intent({"problem": "   "}))
    assert result == _missing_intent_lines()


def test_rationale_none_is_skipped():
    """intent.rationale が None の場合は not provided が表示される。"""
    result = ai_checkpoint.intent_context(_contract_with_intent({"rationale": None}))
    assert result == _missing_intent_lines()


def test_rationale_empty_string_is_skipped():
    """intent.rationale が空文字列の場合は not provided が表示される。"""
    result = ai_checkpoint.intent_context(_contract_with_intent({"rationale": ""}))
    assert result == _missing_intent_lines()


# ---------------------------------------------------------------------------
# constraints のスキップ
# ---------------------------------------------------------------------------


def test_constraints_none_is_skipped():
    """intent.constraints が None の場合は not provided が表示される。"""
    result = ai_checkpoint.intent_context(_contract_with_intent({"constraints": None}))
    assert result == _missing_intent_lines()


def test_constraints_empty_list_is_skipped():
    """intent.constraints が空リストの場合は not provided が表示される。"""
    result = ai_checkpoint.intent_context(_contract_with_intent({"constraints": []}))
    assert result == _missing_intent_lines()


def test_constraints_list_with_empty_string_item_is_skipped():
    """constraints の要素が空文字列の場合は valid 要素のみ表示する。"""
    result = ai_checkpoint.intent_context(
        _contract_with_intent({"constraints": ["valid constraint", "", "  "]})
    )
    assert result == [
        "problem: not provided",
        "constraint: valid constraint",
        "rationale: not provided",
    ]


def test_constraints_non_list_is_skipped():
    """constraints が list でない場合は not provided が表示される。"""
    result = ai_checkpoint.intent_context(_contract_with_intent({"constraints": "not a list"}))
    assert result == _missing_intent_lines()


# ---------------------------------------------------------------------------
# 値が記入済みのフィールドの出力確認
# ---------------------------------------------------------------------------


def test_problem_is_included_when_filled():
    """intent.problem が記入済みの場合は 'problem: ...' の形式で出力される。"""
    result = ai_checkpoint.intent_context(
        _contract_with_intent({"problem": "Scope violations silently pass the validator."})
    )
    assert result == [
        "problem: Scope violations silently pass the validator.",
        "constraint: not provided",
        "rationale: not provided",
    ]


def test_problem_is_stripped():
    """intent.problem の前後の空白はトリムされる。"""
    result = ai_checkpoint.intent_context(
        _contract_with_intent({"problem": "  leading and trailing spaces  "})
    )
    assert result == [
        "problem: leading and trailing spaces",
        "constraint: not provided",
        "rationale: not provided",
    ]


def test_rationale_is_included_when_filled():
    """intent.rationale が記入済みの場合は 'rationale: ...' の形式で出力される。"""
    result = ai_checkpoint.intent_context(
        _contract_with_intent({"rationale": "Backward-compatible optional field."})
    )
    assert result == [
        "problem: not provided",
        "constraint: not provided",
        "rationale: Backward-compatible optional field.",
    ]


def test_constraints_are_included_when_filled():
    """constraints の各要素が 'constraint: ...' の形式で出力される。"""
    result = ai_checkpoint.intent_context(
        _contract_with_intent(
            {"constraints": ["Must remain backward compatible.", "No new required fields."]}
        )
    )
    assert result == [
        "problem: not provided",
        "constraint: Must remain backward compatible.",
        "constraint: No new required fields.",
        "rationale: not provided",
    ]


# ---------------------------------------------------------------------------
# 複合ケース
# ---------------------------------------------------------------------------


def test_all_filled_fields_appear_in_order():
    """problem → constraints → rationale の順に出力される。"""
    result = ai_checkpoint.intent_context(
        _contract_with_intent(
            {
                "problem": "Agents solve the wrong problem.",
                "constraints": ["Must remain backward compatible.", "No new required fields."],
                "rationale": "Optional fields allow gradual adoption.",
            }
        )
    )
    assert result == [
        "problem: Agents solve the wrong problem.",
        "constraint: Must remain backward compatible.",
        "constraint: No new required fields.",
        "rationale: Optional fields allow gradual adoption.",
    ]


def test_partial_intent_only_filled_fields_appear():
    """記入済みのフィールドのみが実値になり、未記入は not provided になる。"""
    result = ai_checkpoint.intent_context(
        _contract_with_intent(
            {
                "problem": "Intent section is not displayed at checkpoint.",
                "constraints": [],
                "rationale": None,
            }
        )
    )
    assert result == [
        "problem: Intent section is not displayed at checkpoint.",
        "constraint: not provided",
        "rationale: not provided",
    ]


def test_unknown_intent_keys_do_not_raise():
    """intent に未知のキーがあっても例外を起こさない（validator が別途検出する）。"""
    result = ai_checkpoint.intent_context(
        _contract_with_intent(
            {
                "problem": "Known problem.",
                "unknownKey": "ignored by intent_context",
            }
        )
    )
    # unknownKey は表示されず、problem のみ実値になる
    assert result == [
        "problem: Known problem.",
        "constraint: not provided",
        "rationale: not provided",
    ]
