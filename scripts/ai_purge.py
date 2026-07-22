"""Evidence-first, double-confirmation purge gate."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


def purge(
    facts: dict[str, Any], confirm_one: bool = False, confirm_two: bool = False
) -> dict[str, Any]:
    """Return a receipt or a blocking proposal; never removes protected paths."""
    deletable = [
        item for item in facts.get("candidates", []) if item not in set(facts.get("protected", []))
    ]
    proposal = {
        "state": "needs_human_confirmation",
        "deletionList": deletable,
        "protected": facts.get("protected", []),
        "warning": "purge is irreversible; export evidence before deletion",
        "writes": [],
    }
    if not facts.get("exportVerified"):
        proposal.update(
            {
                "state": "blocked",
                "reason": "evidence_export_not_verified",
                "resumeCondition": "complete and verify export bundle",
            }
        )
        return proposal
    if not (confirm_one and confirm_two):
        return proposal
    digest = sha256(json.dumps(deletable, sort_keys=True).encode()).hexdigest()
    return {
        "state": "purged",
        "deletionList": deletable,
        "protected": facts.get("protected", []),
        "evidenceDigest": digest,
        "receipt": {"state": "purged", "evidenceDigest": digest},
        "writes": ["purge_receipt"],
    }
