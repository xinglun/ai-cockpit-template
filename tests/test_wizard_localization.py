from __future__ import annotations

import pytest

from ai_wizard_localization import (
    SUPPORTED_LANGUAGES,
    load_messages,
    normalize_language,
    resolve_language,
    validate_parity,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ja", "ja"),
        ("ja-JP", "ja"),
        ("en-US", "en"),
        ("en-GB", "en"),
        ("zh", "zh-CN"),
        ("zh-Hans", "zh-CN"),
    ],
)
def test_language_aliases(value: str, expected: str) -> None:
    assert normalize_language(value) == expected


def test_language_precedence_and_ja_default(monkeypatch) -> None:
    monkeypatch.setenv("AI_COCKPIT_LANGUAGE", "zh")
    assert resolve_language(explicit="en-US", environ="zh", system_locale="ja-JP") == "en"
    assert resolve_language(explicit=None, environ="zh", system_locale="ja-JP") == "zh-CN"
    monkeypatch.delenv("AI_COCKPIT_LANGUAGE")
    assert resolve_language(explicit=None, environ=None, system_locale="en-US") == "en"
    assert resolve_language(explicit=None, environ=None, system_locale=None) == "ja"


def test_all_message_resources_have_exact_key_and_placeholder_parity() -> None:
    messages = {language: load_messages(language) for language in SUPPORTED_LANGUAGES}
    assert validate_parity(messages) == []


def test_unknown_language_fails_without_user_visible_fallback() -> None:
    with pytest.raises(ValueError, match="unsupported language"):
        normalize_language("fr")
