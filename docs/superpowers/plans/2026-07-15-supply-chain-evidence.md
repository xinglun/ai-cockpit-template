---
author: Codex
title: "Supply-chain Evidence Implementation Plan"
description: "在同步后的 main 上重新实施 SBOM 与发布证据链改进。"
keywords:
  - sbom
  - provenance
  - release-evidence
  - supply-chain
---

# Supply-chain Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Reimplement the SBOM and release-evidence improvements from `backup/main-ab850` on the synchronized `main` without importing stale governance or release-history changes.

**Architecture:** Keep `scripts/check_supply_chain.py` as the single evidence producer. Normalize lock and vulnerability identities before building CycloneDX documents, then derive provenance and the digest manifest from the same source commit. Preserve the current release workflow and public distribution preparation behavior.

**Tech Stack:** Python 3.10+, `cyclonedx-python-lib`, `pip-audit`, pytest, Makefile AI Cockpit checks.

## Global Constraints

- Start from the synchronized `main` and keep `backup/main-ab850` unchanged.
- Do not cherry-pick the old commit wholesale.
- Do not modify `.github/workflows/**`, `install.sh`, or `requirements-dev.lock`.
- Do not hand-edit `.ai/cockpit/sbom.json`, `.ai/cockpit/provenance.json`, or `.ai/cockpit/release-digests.json`.
- Preserve the immutable `v0.5.26` release and the current PR-first exact-SHA workflow.
- Every behavior change follows a failing focused test, minimal implementation, passing focused test, then refactor.

## File map

- `tests/test_supply_chain.py`: behavior-level tests for lock parsing, CycloneDX metadata, dependency edges, source identity, vulnerability mapping, and evidence drift.
- `scripts/check_supply_chain.py`: normalized evidence model, CycloneDX serialization, vulnerability mapping, and generated artifact commands.
- `tests/test_release_distribution.py`: release metadata and digest binding regression coverage; modify only if the focused evidence changes require it.
- `docs/reference/distribution.md`: document the evidence boundary and what publisher-provided attestation still supplies.
- `.ai/cockpit/sbom.json`, `.ai/cockpit/provenance.json`, `.ai/cockpit/release-digests.json`: generated outputs written by the supply-chain command.
- `release.json`: update only if regenerated evidence requires the current release claims to change; preserve `v0.5.26`.
- `.ai/work-items/**` and `.ai/cockpit/current_status.md`: Work Item evidence and generated status.

### Task 1: Lock parsing and CycloneDX model

**Files:**
- Test: `tests/test_supply_chain.py`
- Modify: `scripts/check_supply_chain.py`

**Interfaces:**
- `parse_requirements_lock(path: Path) -> list[dict[str, Any]]` returns package records with `name`, normalized `version`, `hashes`, and `via`.
- `build_sbom(source_commit: str | None = None) -> dict[str, Any]` returns the serialized CycloneDX document.

- [ ] **Step 1: Add a failing lock parser test.**

  Add a temporary lock fixture containing a continuation backslash, two SHA-256 hashes, and `# via` lines. Assert the package version has no trailing backslash, both hashes are retained, and the `via` entries are present.

- [ ] **Step 2: Run the focused test to verify RED.**

  Run:

  ```bash
  .venv/bin/python -m pytest -q tests/test_supply_chain.py -k 'lock or continuation'
  ```

  Expected: FAIL because the current parser does not consistently retain continuation metadata in the intended normalized record.

- [ ] **Step 3: Add a failing CycloneDX metadata test.**

  Build an SBOM from a temporary lock/workflow fixture and assert:

  ```python
  assert sbom["metadata"]["tools"][0]["name"] == "check_supply_chain"
  assert sbom["metadata"]["component"]["version"] == source_sha
  assert sbom["dependencies"]
  ```

- [ ] **Step 4: Run the metadata test to verify RED.**

  Run:

  ```bash
  .venv/bin/python -m pytest -q tests/test_supply_chain.py -k 'sbom_uses_cyclonedx_identity or dependency_metadata'
  ```

  Expected: FAIL because the current CycloneDX tool model and/or dependency serialization does not expose the intended stable metadata shape.

- [ ] **Step 5: Implement the minimal model change.**

  Use the installed CycloneDX API's `Tool(name=..., version=...)` metadata representation, keep `PackageURL` strings as component keys, register direct package dependencies from `-r` attribution, and register `via` parent-to-child edges only when both packages exist in the lock.

- [ ] **Step 6: Run the focused tests to verify GREEN.**

  Run:

  ```bash
  .venv/bin/python -m pytest -q tests/test_supply_chain.py -k 'lock or continuation or sbom_uses_cyclonedx_identity or dependency_metadata'
  ```

  Expected: PASS with no unrelated test changes.

### Task 2: Vulnerability identity mapping and fail-closed behavior

**Files:**
- Test: `tests/test_supply_chain.py`
- Modify: `scripts/check_supply_chain.py`

**Interfaces:**
- `normalize_package_name(name: str) -> str` is the shared package identity normalizer.
- `map_vulnerabilities_to_sbom(payload: dict[str, Any], sbom: dict[str, Any]) -> list[str]` returns sorted SBOM-linked vulnerability strings or raises for an unknown package identity.

- [ ] **Step 1: Add a failing known-vulnerability mapping test.**

  Supply a pip-audit payload for `demo==1.0.0`, an SBOM component with purl `pkg:pypi/demo@1.0.0`, and assert the output includes `pkg:pypi/demo@1.0.0:CVE-2024-0001 fix=1.0.1`.

- [ ] **Step 2: Run the test to verify RED.**

  Run:

  ```bash
  .venv/bin/python -m pytest -q tests/test_supply_chain.py -k 'vulnerability_scan_parses'
  ```

  Expected: FAIL if the current output does not include the SBOM bom-ref and fix versions.

- [ ] **Step 3: Add a failing unknown-identity test.**

  Pass a vulnerability for `missing==9.9.9` while the SBOM contains no matching library. Assert `map_vulnerabilities_to_sbom` raises `ValueError` containing `cannot be mapped to SBOM component`.

- [ ] **Step 4: Implement minimal normalization and mapping.**

  Index only `library` components with `pkg:pypi/` purls by normalized `(name, version)`. For each pip-audit vulnerability, emit the component bom-ref, vulnerability id, and comma-joined fix versions. Raise before returning if a vulnerable dependency cannot be indexed.

- [ ] **Step 5: Run focused mapping tests to verify GREEN.**

  Run:

  ```bash
  .venv/bin/python -m pytest -q tests/test_supply_chain.py -k 'vulnerability'
  ```

  Expected: PASS.

### Task 3: Evidence generation and release binding

**Files:**
- Test: `tests/test_supply_chain.py`, `tests/test_release_distribution.py`
- Modify: `scripts/check_supply_chain.py` only where focused tests identify missing binding behavior.
- Modify: `docs/reference/distribution.md` if the current evidence explanation lacks the implemented boundary.

- [ ] **Step 1: Add a failing digest consistency test.**

  Generate a temporary SBOM/provenance/manifest fixture, change one byte in the generated SBOM, and assert `compare_or_write(..., write=False)` reports the computed-evidence drift.

- [ ] **Step 2: Run the test to verify RED.**

  Run:

  ```bash
  .venv/bin/python -m pytest -q tests/test_supply_chain.py tests/test_release_distribution.py -k 'digest or supply_chain'
  ```

  Expected: FAIL only if the current digest binding does not cover the changed file.

- [ ] **Step 3: Implement only missing evidence binding.**

  Keep `build_provenance` and `build_release_digests` on the explicit `source_commit` path. Ensure the release manifest covers `requirements-dev.lock`, SBOM, provenance, `install.sh`, and `release.json`, without changing the workflow or installer.

- [ ] **Step 4: Regenerate command-owned evidence.**

  Run:

  ```bash
  .venv/bin/python scripts/check_supply_chain.py sbom --write --source-commit origin/main
  .venv/bin/python scripts/check_supply_chain.py provenance --write --source-commit origin/main
  .venv/bin/python scripts/check_supply_chain.py release --write --source-commit origin/main
  ```

- [ ] **Step 5: Verify focused evidence and distribution tests.**

  Run:

  ```bash
  .venv/bin/python -m pytest -q tests/test_supply_chain.py tests/test_release_distribution.py
  ```

  Expected: PASS.

### Task 4: Documentation and full verification

**Files:**
- Modify: `docs/reference/distribution.md`
- Modify: `.ai/work-items/active/supply_chain_evidence.summary.json`
- Generate: `.ai/cockpit/current_status.md`

- [ ] **Step 1: Document the verified boundary.**

  State that the digest manifest proves repository-internal consistency only, while signatures, attestations, and an external trust root remain publisher responsibilities. Keep the current PR-first exact-SHA release sequence unchanged.

- [ ] **Step 2: Run the full project quality suite.**

  Run:

  ```bash
  make quality
  ```

  Expected: all local checks pass; any post-publication check must be recorded with its reason if the tag is not being changed in this Work Item.

- [ ] **Step 3: Run Work Item governance checks.**

  Run:

  ```bash
  make ai-checkpoint CONTRACT=.ai/work-items/active/supply_chain_evidence.contract.json SUMMARY=.ai/work-items/active/supply_chain_evidence.summary.json STAGE=before_edit
  make ai-finish TASK=supply_chain_evidence
  make check-ai-pr AI_BASE_COMMIT=origin/main
  ```

  Expected: the summary records command evidence, the Work Item archives, Cockpit status becomes `no_active_work_item`, and the aggregate PR ownership check passes.

- [ ] **Step 4: Inspect the final diff and commit the implementation.**

  Run:

  ```bash
  git diff origin/main...HEAD --check
  git diff --stat origin/main...HEAD
  git status --short --branch
  ```

  Expected: only the declared supply-chain implementation, tests, documentation, generated evidence, and Work Item records are present.
