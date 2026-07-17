"""Tests for the strict, language-neutral Trust Layer schema foundation."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

import ai_trust_schema


ROOT = Path(__file__).resolve().parents[1]


def test_all_trust_schemas_and_examples_are_valid() -> None:
    schemas = ai_trust_schema.validate_schema_documents()
    assert set(schemas) == ai_trust_schema.SCHEMA_NAMES


@pytest.mark.parametrize("name", sorted(ai_trust_schema.SCHEMA_NAMES))
def test_schema_examples_reject_unknown_root_fields(name: str) -> None:
    schema = ai_trust_schema.load_schemas()[name]
    payload = copy.deepcopy(schema["examples"][0])
    payload["unexpected"] = True

    with pytest.raises(ai_trust_schema.ValidationError, match="unknown field"):
        ai_trust_schema.validate(payload, schema)


def test_human_decision_request_requires_all_explain_before_asking_fields() -> None:
    schema = ai_trust_schema.load_schemas()["human_decision_request"]
    payload = copy.deepcopy(schema["examples"][0])
    del payload["recommendationReason"]

    with pytest.raises(ai_trust_schema.ValidationError, match="recommendationReason.*required"):
        ai_trust_schema.validate(payload, schema)


def test_human_decision_request_requires_at_least_two_options() -> None:
    schema = ai_trust_schema.load_schemas()["human_decision_request"]
    payload = copy.deepcopy(schema["examples"][0])
    payload["options"] = payload["options"][:1]

    with pytest.raises(ai_trust_schema.ValidationError, match="at least 2"):
        ai_trust_schema.validate(payload, schema)


def test_schema_version_and_enum_mismatches_are_rejected() -> None:
    schema = ai_trust_schema.load_schemas()["human_decision_evidence"]
    payload = copy.deepcopy(schema["examples"][0])
    payload["schemaVersion"] = 2
    with pytest.raises(ai_trust_schema.ValidationError, match="constant"):
        ai_trust_schema.validate(payload, schema)

    payload = copy.deepcopy(schema["examples"][0])
    payload["source"] = "agent_self_declaration"
    with pytest.raises(ai_trust_schema.ValidationError, match="one of"):
        ai_trust_schema.validate(payload, schema)


def test_cli_check_runs_against_repository_schemas() -> None:
    assert ai_trust_schema.main(["--check"]) == 0


def test_schema_directory_contains_only_expected_documents() -> None:
    files = {
        path.name.removesuffix(".schema.json")
        for path in (ROOT / ".ai" / "trust" / "schema").glob("*.schema.json")
    }
    assert files == ai_trust_schema.SCHEMA_NAMES
