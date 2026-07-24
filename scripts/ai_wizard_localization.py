"""Language normalization and exact-parity message resources for the Wizard."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Mapping

SUPPORTED_LANGUAGES = ("ja", "en", "zh-CN")
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "locales" / "wizard"


def normalize_language(value: str) -> str:
    """Normalize a supported language alias, rejecting silent fallback."""
    normalized = value.strip().lower().replace("_", "-")
    if normalized == "ja" or normalized.startswith("ja-"):
        return "ja"
    if normalized in {"en", "en-us", "en-gb"}:
        return "en"
    if normalized in {"zh", "zh-cn", "zh-hans"}:
        return "zh-CN"
    raise ValueError(f"unsupported language: {value}")


def resolve_language(
    *, explicit: str | None, environ: str | None = None, system_locale: str | None = None
) -> str:
    """Resolve explicit, environment, system locale, then the safe ``ja`` default."""
    candidates = (
        explicit,
        environ if environ is not None else os.environ.get("AI_COCKPIT_LANGUAGE"),
        system_locale,
    )
    for candidate in candidates:
        if candidate and candidate.strip():
            return normalize_language(candidate)
    return "ja"


def load_messages(language: str) -> dict[str, str]:
    """Load one Wizard resource file after strict language normalization."""
    normalized = normalize_language(language)
    path = _RESOURCE_DIR / f"{normalized}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Wizard resource: {path}") from exc
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(text, str) for key, text in value.items()
    ):
        raise ValueError(f"Wizard resource must be a string map: {path}")
    return value


def _placeholders(text: str) -> frozenset[str]:
    return frozenset(_PLACEHOLDER.findall(text))


def validate_parity(messages: Mapping[str, Mapping[str, str]]) -> list[str]:
    """Return key/placeholder parity errors across all supplied languages."""
    errors: list[str] = []
    if not messages:
        return ["no Wizard message resources supplied"]
    reference_language = next(iter(messages))
    reference = messages[reference_language]
    for language, resource in messages.items():
        missing = sorted(set(reference) - set(resource))
        extra = sorted(set(resource) - set(reference))
        if missing:
            errors.append(f"{language}: missing keys: {', '.join(missing)}")
        if extra:
            errors.append(f"{language}: extra keys: {', '.join(extra)}")
        for key in sorted(set(reference) & set(resource)):
            expected = _placeholders(reference[key])
            actual = _placeholders(resource[key])
            if expected != actual:
                errors.append(f"{language}.{key}: placeholder mismatch")
    return errors


def validate_builtin_parity() -> None:
    """Raise when checked-in resources drift from exact parity."""
    messages = {language: load_messages(language) for language in SUPPORTED_LANGUAGES}
    errors = validate_parity(messages)
    if errors:
        raise ValueError("; ".join(errors))
