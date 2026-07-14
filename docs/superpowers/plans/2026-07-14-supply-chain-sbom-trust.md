---
author: Ray
title: "Supply-Chain SBOM and Release Trust Implementation Plan"
description: "修复 SBOM 语义、漏洞关联和发布证据链的实施计划。"
keywords:
  - sbom
  - cyclonedx
  - supply-chain
  - release
---

# Supply-Chain SBOM and Release Trust Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct lock/SBOM semantics, map vulnerability findings to SBOM identities, and make release evidence independently verifiable up to the repository's explicit signing boundary.

**Architecture:** Keep one supply-chain entry point, but split its data flow into structured lock records, CycloneDX model serialization, normalized vulnerability identity mapping, and generated digest-manifest validation. Generated baselines remain command-owned.

**Tech Stack:** Python 3.10+, `cyclonedx-python-lib`, `pip-audit`, pytest, Makefile checks, JSON evidence.

## Global Constraints

- No private signing keys, credentials, or machine-specific configuration.
- Do not hand-edit generated SBOM, provenance, manifest, or status files.
- Preserve explicit source-commit resolution and release-tag compatibility.
- Fail closed when vulnerability findings cannot map to an SBOM component.

### Task 1: Lock parsing and SBOM identity regression tests

**Files:**
- Modify: `tests/test_supply_chain.py`
- Modify: `scripts/check_supply_chain.py`

- [ ] Write tests for stripped continuation characters, per-component hashes, stable purls/bom-refs, CycloneDX metadata, and dependency references.
- [ ] Run the focused tests and confirm they fail for the current hand-built SBOM.
- [ ] Implement structured lock parsing and CycloneDX model serialization using the installed library.
- [ ] Run the focused tests and the existing supply-chain tests.

### Task 2: Vulnerability mapping and release evidence tests

**Files:**
- Modify: `tests/test_supply_chain.py`
- Modify: `scripts/check_supply_chain.py`

- [ ] Add a pip-audit fixture asserting a finding carries the matching component `bom-ref`.
- [ ] Add a test asserting an unknown finding fails closed.
- [ ] Add a test for generated digest-manifest consistency and drift detection.
- [ ] Implement shared package identity normalization, vulnerability mapping, and manifest generation/validation.
- [ ] Run focused tests and regenerate evidence through the command.

### Task 3: Documentation and generated release evidence

**Files:**
- Modify: `docs/reference/distribution.md`
- Modify: `.ai/cockpit/sbom.json`
- Modify: `.ai/cockpit/provenance.json`
- Modify: `release.json`

- [ ] Document what the digest manifest proves and what requires publisher-provided signatures or attestations.
- [ ] Generate SBOM, provenance, and release digest evidence from the approved source commit.
- [ ] Verify no generated file was hand-edited and inspect all library versions for continuation characters.

### Task 4: Full verification and Cockpit handoff

**Files:**
- Modify: `.ai/work-items/active/supply-chain-sbom-trust.summary.json`
- Modify: `.ai/cockpit/current_status.md`

- [ ] Run project tests, format, lint, type, supply-chain, and all Contract-required AI checks.
- [ ] Record exact verification results, guideline compliance, checkpoint evidence, residual risks, and known gaps in the Summary.
- [ ] Generate and validate Cockpit status, then run `make ai-finish TASK=supply-chain-sbom-trust`.
