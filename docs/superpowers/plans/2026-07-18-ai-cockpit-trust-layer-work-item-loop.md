---
author: Codex
title: "AI Cockpit Trust Layer Work Item Loop"
description: "Ordered Work Item plan for implementing, releasing, and closing the AI Cockpit Trust Layer upgrade."
keywords:
  - ai-cockpit
  - trust-layer
  - work-items
  - governance
---

# AI Cockpit Trust Layer Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Trust Layer specification into ten sequential Work Items that can be executed through the complete AI Cockpit lifecycle and then hand off automatically to the next item.

**Architecture:** PR1–PR8 implement the Trust Layer in dependency order. PR9 publishes the resulting repository release. PR10 deletes this execution plan only after all preceding evidence is archived and the release is verified. Each Work Item is an independent review unit with its own Contract, branch, Summary, checks, PR, merge, and lifecycle closure.

**Tech Stack:** AI Cockpit Work Item Contracts v2, Python governance scripts, Make targets, YAML/JSON schemas, repository documentation, automated tests, and the repository’s configured release tooling.

## Global Constraints

- Stop before implementation when capability, intent, risk, or success criteria are unclear.
- Evidence must come from structured records or machine-verifiable checks; agent self-declaration is insufficient.
- Human decisions must be recorded as Decision Evidence and followed by a fresh Preflight run.
- One Work Item, one dedicated branch, and one PR; do not combine independent items.
- Start each template-maintenance branch from the latest `origin/main` and record the base commit.
- Do not merge into local `main` before the PR is merged; run `make ai-close-work-item TASK=<task>` only after merge.
- The user has authorized the requested sequence, including release and final plan deletion; this authorization does not bypass repository/provider safety gates, required evidence, or fail-closed checks.
- The final deletion is destructive and must be limited to this plan file plus any explicitly generated references that the deletion Work Item declares.

## Loop Controller

Execute the following controller for `N = 1..10`:

1. Select the next Work Item from the ordered table and create its v2 Contract with `make ai-start TASK=<task> TITLE="..." MODE=code`.
2. Run `make ai-preflight`; if the result is `needs_human_confirmation` or `not_ready`, stop and present the generated decision request. Resume only after valid Decision Evidence is recorded and a fresh Preflight reports `ready`.
3. Create the dedicated branch from the latest remote default base, implement only the declared scope, and run the Contract’s required checks.
4. Run `make ai-checkpoint STAGE=before_finish`, update the Summary with changed files, evidence, scenario coverage, risks, and review readiness, then run `make ai-finish TASK=<task>`.
5. Push the branch, open and merge its PR using the repository’s required review process. Do not enable branch deletion before closure can identify the branch.
6. Run `make ai-close-work-item TASK=<task>`. Continue only when it reports `ready for next Work Item` and the base is clean and synchronized.
7. Increment `N` and execute the next row. After Work Item 10 closes, report the complete evidence chain and stop.

If any command fails, preserve the Work Item state, record the failure in its Summary, and follow the repository’s remediation/review path; do not silently skip to the next row. The only planned destructive action is Work Item 10.

## Work Item Order

| # | Task ID | Deliverable | Depends on |
|---:|---|---|---|
| 1 | `trust_schema_foundation` | Repository Capability, Success Criteria, Human Decision Request/Evidence, and Baseline schemas plus validators | none |
| 2 | `trust_capability_intent_guards` | Capability, ambiguous-intent, constraint-conflict, and Success Criteria completeness guards wired into Preflight | 1 |
| 3 | `trust_human_decision_protocol` | Decision Request generation, persistence, IDs, resume conditions, and post-decision Preflight rerun | 1–2 |
| 4 | `trust_critical_domain_guards` | Critical-domain, governance-bypass, evidence-forgery, and production-operation guards | 1–3 |
| 5 | `trust_baseline_backtrack_evidence` | Before/after test, coverage, scenario, file, and protected-asset evidence | 1–4 |
| 6 | `trust_cockpit_cli_presentation` | CLI, Cockpit Status, Summary, exit codes, recommendations, and machine-readable output | 1–5 |
| 7 | `trust_negative_scenario_suite` | At least ten negative scenarios proving safe stop, evidence, decisions, and recovery | 1–6 |
| 8 | `trust_documentation_demo` | README, architecture, philosophy, guides, demo, and failure demonstrations | 1–7 |
| 9 | `trust_publish_release` | Verify release readiness and publish the new version from the merged, green base | 1–8 |
| 10 | `trust_delete_execution_plan` | Delete this execution plan after all work and release evidence is archived | 1–9 |

### Task 1: Schema Foundation

**Scope:** Add the five Trust Layer data contracts and equivalent schema validation. Include required fields for status, evidence, options, recommendation, decision identity, resume condition, and baseline provenance.

**Acceptance:** Valid examples pass; missing required Human Decision Request or Evidence fields fail; schema versions are explicit; no implementation assumes a specific LLM.

**Verification:** Contract checks, schema validator tests, malformed-payload tests, and project quality checks.

**Handoff:** Archive the Work Item and close it before starting Task 2.

### Task 2: Capability and Intent Guards

**Scope:** Implement project-owned capability matching, ambiguous-intent detection, constraint conflict checks, and Success Criteria completeness checks; integrate them into Preflight.

**Acceptance:** Supported requests can reach `ready`; ambiguous or unsupported requests stop before implementation and expose evidence, options, recommendation, question, and resume condition.

**Verification:** Positive/negative guard tests, Preflight output checks, and zero-change-before-confirmation checks.

**Handoff:** Continue only after Task 1 is archived and Task 2 is closed.

### Task 3: Human Decision Protocol

**Scope:** Generate and persist Human Decision Requests, assign stable Decision IDs, record decisions under `.ai/decisions/`, enforce resume conditions, and require a fresh Preflight after the decision.

**Acceptance:** Chat text alone cannot satisfy confirmation; stale, mismatched, or missing evidence remains blocked; a valid decision followed by a new `ready` Preflight can resume.

**Verification:** Decision schema tests, hash/identity mismatch tests, persistence tests, and rerun-state tests.

**Handoff:** The next task may start only after the decision protocol itself is archived and closed.

### Task 4: Critical Domain and Governance Guards

**Scope:** Add policy-first detection for authentication, authorization, payment, personal data, secrets, production release, and governance bypass. Add evidence-forgery and production-operation rejection paths.

**Acceptance:** High-risk operations require approval or are rejected; bypass requests cannot finish, become Done, pass PR checks, or publish a release; safe test/local alternatives are presented where appropriate.

**Verification:** Critical-domain fixtures, bypass tests, forgery tests, production-operation tests, and fail-closed finish checks.

**Handoff:** Close the task only after all blocked paths leave machine-readable evidence.

### Task 5: Baseline and Backtrack Evidence

**Scope:** Capture pre-change test, coverage, scenario, file-count, and protected-asset baselines and compare them with after-change evidence without inventing unavailable values.

**Acceptance:** Deletion or quality regression is visible before completion; absent historical baselines are reported as unavailable; comparisons cite commit and capture time.

**Verification:** Baseline fixture tests, regression tests, missing-baseline tests, and evidence-chain checks.

**Handoff:** Only a closed Task 5 with verified baseline evidence unlocks presentation work.

### Task 6: Cockpit and CLI Presentation

**Scope:** Update CLI output, generated Cockpit Status, Summary fields, exit codes, human-readable recommendations, and machine-readable JSON for stop/review/resume states.

**Acceptance:** A reviewer can see what happened, why it matters, evidence, options, recommendation, decision, and resume condition; generated status is never hand-edited.

**Verification:** Golden output tests, status generation/checks, exit-code tests, Summary validation, and consistency checks.

**Handoff:** Close only after status and Summary agree with actual evidence.

### Task 7: Negative Scenario Suite

**Scope:** Automate at least ten negative scenarios: capability boundary, critical business risk, quality regression, governance bypass, ambiguous intent, production operation, security-check deletion, forged evidence, scope expansion, and conflicting goals.

**Acceptance:** Every scenario checks final state, stop behavior, unauthorized changes, explanation, options, recommendation, decision recording, and revalidation after recovery. Produce a machine-readable aggregate report with unsafe operations and unauthorized changes counts.

**Verification:** The complete negative suite, report schema validation, and project quality checks.

**Handoff:** Task 8 starts only when the suite is green and its evidence is archived.

### Task 8: Documentation and Demo

**Scope:** Update README, design philosophy, architecture, Work Item guide, adopter guide, demo script, and failure demonstrations around “AI Cockpit knows when to stop.”

**Acceptance:** Documentation describes the Trust Layer boundary, evidence model, human decision protocol, safe recovery, and non-goals; examples do not imply that LLM explanations are evidence.

**Verification:** Documentation metadata/link checks, rendered examples where configured, project checks, and a demo run showing zero unsafe operations and intact evidence.

**Handoff:** Start release preparation only from the merged and verified base.

### Task 9: Publish New Version

**Scope:** Prepare release metadata, run the full release/distribution/evidence gates, publish the new version from the merged base, and record tag, commit, artifacts, checks, and provenance.

**Acceptance:** Release source and version metadata match; release checks and distribution checks pass; the published tag points to the reviewed merged commit; release evidence is archived.

**Verification:** `make quality`, release evidence/distribution checks, exact-commit/tag verification, and the repository’s configured publication smoke checks.

**Authorization:** The user has authorized publication in this requested sequence. The Work Item must still fail closed on missing credentials, failed checks, mismatched tag/source, or provider confirmation requirements.

**Handoff:** Do not delete the plan until the release is independently verified and Task 9 is closed.

### Task 10: Delete Execution Plan

**Scope:** Delete only `docs/superpowers/plans/2026-07-18-ai-cockpit-trust-layer-work-item-loop.md` and any generated references explicitly included in the Contract. Preserve all Contracts, Summaries, archived evidence, release metadata, and user-facing documentation required for auditability.

**Acceptance:** The plan is absent, no active Work Item depends on it, all ten Work Items and release evidence remain discoverable, and the final diff contains no unrelated deletion.

**Verification:** Scope/ownership checks, archive/index/status consistency checks, full PR audit, and final clean-worktree verification.

**Authorization:** The user has explicitly requested deletion as the final Work Item. Because deletion is destructive, record the authorization and exact allow-pattern in Task 10’s Contract; do not generalize it to other files.

**Handoff:** Close Task 10 only after its PR is merged and `make ai-close-work-item TASK=trust_delete_execution_plan` reports the final clean, synchronized state.

## Completion Report

The controller is complete only when Task 10 is closed. The final report must include the ten Work Item IDs, each archived Contract/Summary location, PR/merge evidence, release tag and commit, deletion scope, required-check results, residual risks, and the final Cockpit state. It must not claim that any external release or deletion occurred unless the corresponding evidence exists.
