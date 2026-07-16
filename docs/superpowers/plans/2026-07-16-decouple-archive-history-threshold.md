---
author: Codex
title: "Decouple Immutable Archive History from Complexity Thresholds Implementation Plan"
description: Implementation plan for separating immutable archive history from current complexity limits.
keywords:
  - governance
  - archive
  - complexity
---

# Decouple Immutable Archive History from Complexity Thresholds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop cumulative immutable archive counts from blocking current complexity checks while preserving archive integrity and current-PR ownership validation.

**Architecture:** Keep archive counts in the generated governance-complexity report as observational metrics. Remove only archive count fields from the blocking policy limit set and retain all archive pair/index validation as blocking. The existing PR audit remains the authority for changed archive-pair ownership.

**Tech Stack:** Python, pytest, YAML, Markdown, Make, AI Cockpit Work Item Contract/Summary.

## Global Constraints

- Do not delete, rewrite, compact, or relocate historical archive evidence.
- Do not change current-PR archive ownership rules.
- Do not change the semantics of tracked-file, Python-line, or Markdown-line thresholds; calibrate their ceilings only as needed to include this Work Item's required governance documents.
- Use the active Work Item Contract as the change boundary.
- Verify behavior with a failing test before implementation changes.

### Task 1: Lock the new archive-threshold behavior with tests

**Files:**
- Modify: `tests/test_governance_complexity.py`

**Interfaces:**
- Consumes: `check_governance_complexity.build_report` and `policy` test helper.
- Produces: regression coverage proving archive totals above 260 are observational, while integrity failures remain errors.

- [ ] **Step 1: Add a failing test for totals above the former threshold**

Add a test that creates 261 valid Contract/Summary pairs and a matching index, configures non-archive limits above the fixture size, calls `build_report`, and asserts no issue mentions archive count limits while the reported metrics equal 261.

- [ ] **Step 2: Run the focused test and verify it fails for the expected reason**

Run:

```bash
pytest -q tests/test_governance_complexity.py::test_archive_totals_are_observational_above_former_threshold
```

Expected: FAIL because the current policy loader requires archive count limits and the current checker compares cumulative totals against them.

- [ ] **Step 3: Confirm existing integrity failure tests remain meaningful**

Run:

```bash
pytest -q tests/test_governance_complexity.py::test_report_fails_on_threshold_and_missing_archive_pair tests/test_governance_complexity.py::test_archive_metrics_reports_missing_and_malformed_index_entries
```

Expected: existing tests pass before the production change, establishing that they exercise the archive integrity paths.

### Task 2: Remove cumulative archive counts from blocking policy limits

**Files:**
- Modify: `scripts/check_governance_complexity.py`
- Modify: `.ai/guards/governance_complexity_policy.yaml`
- Test: `tests/test_governance_complexity.py`

**Interfaces:**
- Consumes: archive metrics returned by `archive_metrics` and the policy `max` mapping.
- Produces: reports containing archive totals without treating those totals as blocking limits.

- [ ] **Step 1: Update policy loading to require only live complexity limits**

Change `load_policy` so its required metric tuple contains only `trackedFiles`, `pythonLines`, and `markdownLines`. Keep `archiveContracts` and `archiveSummaries` in `archive_metrics` and in the report’s `metrics` mapping.

- [ ] **Step 2: Remove archive count max entries from the policy YAML**

Delete only `archiveContracts` and `archiveSummaries` from `.ai/guards/governance_complexity_policy.yaml`; leave all other values unchanged.

- [ ] **Step 3: Update policy tests and make the focused regression pass**

Adjust test fixtures so policies contain only the three blocking limits, then run:

```bash
pytest -q tests/test_governance_complexity.py
```

Expected: PASS, including the new above-threshold observational test and all existing integrity failures.

### Task 3: Document the boundary between history and current work

**Files:**
- Modify: `docs/reference/governance-complexity.md`

**Interfaces:**
- Consumes: the implemented checker/policy behavior and existing PR audit documentation.
- Produces: maintainer guidance that distinguishes observational archive totals, blocking archive integrity, and current-PR ownership.

- [ ] **Step 1: Update the report description**

State that archive Contract/Summary counts are reported for visibility but are not cumulative blocking limits.

- [ ] **Step 2: Document blocking archive checks**

State that pair completeness, index shape, and index path existence remain blocking failures.

- [ ] **Step 3: Document current-PR ownership**

State that newly changed archive evidence is validated by `make check-ai-pr`, independently of historical archive totals.

- [ ] **Step 4: Run documentation and focused validation**

Run:

```bash
make check-docs-metadata
pytest -q tests/test_governance_complexity.py
```

Expected: both commands pass.

### Task 4: Run Work Item verification and archive the evidence

**Files:**
- Modify: `.ai/work-items/active/decouple_archive_history_threshold.contract.json`
- Modify: `.ai/work-items/active/decouple_archive_history_threshold.summary.json`
- Generate: `.ai/cockpit/current_status.md`
- Generate/archive: `.ai/work-items/archive/**`

**Interfaces:**
- Consumes: completed implementation, tests, and required Make checks.
- Produces: immutable archived Contract/Summary evidence and a consistent no-active Cockpit status.

- [ ] **Step 1: Run the required project and AI checks through Make**

Run the Contract-declared checks, including `make quality`, `make check-governance-complexity`, `make check-ai-pr AI_BASE_COMMIT=origin/main`, and the required status/ownership checks. Record every result in the Summary.

- [ ] **Step 2: Run the before-finish checkpoint**

Run:

```bash
make ai-checkpoint CONTRACT=.ai/work-items/active/decouple_archive_history_threshold.contract.json SUMMARY=.ai/work-items/active/decouple_archive_history_threshold.summary.json STAGE=before_finish
```

Record the checkpoint evidence in the Summary.

- [ ] **Step 3: Run `make ai-finish` and archive the Work Item**

Update the Summary with changed files, verification results, guideline compliance, residual risks, and review readiness. Then run `make ai-finish TASK=decouple_archive_history_threshold`; archive only after all checks pass.

- [ ] **Step 4: Verify final repository state**

Run `make check-ai-status-consistency`, `make check-governance-complexity`, and `git diff --check`. Confirm the archive count is reported but no longer causes the complexity check to fail.
