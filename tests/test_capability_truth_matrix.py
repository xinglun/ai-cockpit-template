"""Regression checks for the Conditional GO capability truth boundary."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs/reference/capability-truth-matrix.json"
MARKDOWN_PATH = ROOT / "docs/reference/capability-truth-matrix.md"


def load_matrix() -> dict:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def test_matrix_uses_closed_status_vocabulary_and_evidence_fields() -> None:
    matrix = load_matrix()
    statuses = set(matrix["statusVocabulary"])
    assert statuses == {"implemented", "template_only", "adopter_installed", "planned"}
    assert matrix["capabilities"]
    for capability in matrix["capabilities"]:
        assert capability["status"] in statuses
        assert capability["id"]
        assert capability["claim"]
        assert capability["evidence"]
        if capability["status"] == "planned":
            assert capability.get("missingEvidence")


def test_remaining_review_gaps_and_completed_evidence_are_explicit() -> None:
    capabilities = {item["id"]: item for item in load_matrix()["capabilities"]}
    assert capabilities["quick_install_release_archive_digest"]["status"] == "planned"
    assert capabilities["independent_ci_release_evidence"]["status"] == "implemented"


def test_matrix_document_points_to_machine_readable_source_and_plan() -> None:
    document = MARKDOWN_PATH.read_text(encoding="utf-8")
    assert "capability-truth-matrix.json" in document
    assert "2026-07-22-conditional-go-review-remediation.md" in document
    assert "template_only" in document
    assert "adopter_installed" in document
