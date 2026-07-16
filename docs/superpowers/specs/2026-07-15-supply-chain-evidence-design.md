---
author: Codex
title: "Supply-chain evidence reimplementation"
description: "从最新 main 重新实施 SBOM 与发布证据链改进，不回退当前治理与发布流程。"
keywords:
  - sbom
  - provenance
  - release-evidence
  - supply-chain
---

# Supply-chain evidence reimplementation

## Problem and goal

`backup/main-ab850` contains a useful SBOM and release-evidence improvement, but
its parent is stale and the commit also removes or rewinds unrelated governance
and release changes. The goal is to reimplement only the supply-chain behavior
on the synchronized `main`, preserving the previous published release contract and
the current workflow files.

## Scope

The implementation is limited to the supply-chain evidence boundary:

- `scripts/check_supply_chain.py` for structured lock parsing, CycloneDX model
  serialization, stable component identity, dependency relationships, and
  vulnerability-to-SBOM mapping.
- `scripts/check_release_distribution.py` for release evidence digest checks
  and fail-closed validation behavior.
- Focused tests in `tests/test_supply_chain.py` and
  `tests/test_release_distribution.py`.
- Command-generated `.ai/cockpit/sbom.json`, `provenance.json`, and
  `release-digests.json` plus the related distribution documentation.

Current release and governance workflows, installer defaults, historical
archive records, and unrelated AI Cockpit scripts are non-goals.

## Design

The existing supply-chain command remains the single entry point. It will:

1. Parse the lock file into normalized package records, preserving hashes and
   `via` relationships.
2. Parse pinned GitHub Actions from workflows.
3. Serialize a CycloneDX document with the application as the root component,
   stable purls/bom-refs, dependency edges, deterministic metadata, and the
   checker tool identity.
4. Normalize pip-audit package identities and map each vulnerability to the
   matching SBOM component. Unknown identities fail closed.
5. Generate provenance and a digest manifest over the lock, SBOM, provenance,
   installer, and release metadata.

`check_release_distribution.py` remains responsible for validating the
release.json digest claims against the inspected tree. The release workflow is
not changed; publication still requires the exact merged `main` SHA and the
existing smoke/compatibility gates.

## Test strategy

Tests will be written or adapted before implementation and must first fail for
the current behavior. The focused suite will cover:

- continuation-character stripping and lock metadata semantics;
- stable purls, bom-refs, CycloneDX metadata, and dependency edges;
- vulnerability mapping to a known component and rejection of an unknown one;
- generated release digest consistency and drift detection;
- explicit source-commit resolution independent of ambient Git variables;
- preservation of current release-preparation and public distribution behavior.

After the focused red/green cycles, run the full project quality suite and all
AI Cockpit checks. Generated evidence will only be changed through
`scripts/check_supply_chain.py`.

## Failure and rollback behavior

Evidence generation and validation fail closed on malformed lock entries,
missing hashes, unmapped vulnerability identities, digest drift, or an invalid
source commit. If implementation or review is rejected, revert the new PR;
the immutable public tag and its release assets are not rewritten.

## Acceptance

The resulting PR must contain only the declared supply-chain changes and Work
Item evidence, preserve the current workflow files byte-for-byte, pass focused
and full verification, and leave the release system able to validate future
exact-SHA publications.
