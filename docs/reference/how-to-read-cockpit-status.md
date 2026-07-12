---
author: Ray
title: "How to Read Cockpit Status"
description: Reviewer-facing guide to interpreting AI Cockpit current_status.md during V2.5/V2.6 stabilization.
keywords:
  - ai-cockpit
  - cockpit-status
  - reviewer-guide
  - release-hardening
  - v2.5
---

# How to Read Cockpit Status

This page explains how to read the generated Cockpit Status during V2.5/V2.6 stabilization and release hardening.
It is written for reviewers, maintainers, and approvers who want the shortest path from status to decision.
If you are about to start implementation, read the latest Preflight Review first. Cockpit Status is for reviewer visibility; it does not replace the pre-implementation pause.

## Read Order

Start with these fields in order:

1. `Preflight Review` if present in the active Work Item workflow
2. `Recommendation`
3. `Decision Drivers`
4. `Governance Signals`
5. `Evidence`
6. `Scenario Coverage` if present in the signals list

`Preflight Review` derives implementation readiness from Contract evidence. It is advisory by default and should be shown before coding starts.

`Recommendation` gives the decision state. `Decision Drivers` explains why that state was chosen.
`Governance Signals` show the compressed judgment, and `Evidence` points back to the repository truth.

## What the Preflight Review Means

| Status | Meaning |
| --- | --- |
| `ready` | The Contract evidence is sufficient to begin implementation without a human clarification pause. |
| `needs_human_confirmation` | The Contract evidence is usable, but the reviewer should clarify the missing or weak signals before coding continues. |
| `not_ready` | The Contract evidence does not yet support implementation, so the pause should continue until the gap is resolved. |

The review is an advisory view, not an AI confidence statement. It is derived from existing Contract evidence such as `intent`, `unknowns`, `sources`, `acceptance`, `scope`, `outOfScope`, `riskAssessment`, `scenarioCoverage`, and `verification`.

### Explicit blockers

The report is `not_ready` immediately when `notCodable` is `true`; when `executionDecision.status` is `block`, `defer`, or `needs_human_decision`; or when a declared `agentCapability` cannot implement, cannot verify, or needs a human decision. For example, `{"notCodable": true}` is not a request for more confidence: implementation must pause until the Contract changes.

## No Active Work Item

`no_active_work_item` means no Contract/Summary pair is active. It does **not** mean the worktree is unchanged: the generated no-active status intentionally omits the file list, but it now surfaces a compressed `Worktree Changes` signal, a count, and an `Ownership Preview` state so dirty trees do not read as `none`. Use `make check-ai-diff-ownership` for a local ownership preview and `make check-ai-pr AI_BASE_COMMIT=<merge-base>` for final PR audit. In PR mode the audit resolves overlapping archive claims deterministically, with the latest matching archive pair winning.

## What the Recommendation Means

| Recommendation | Meaning |
| --- | --- |
| `ready_for_review` | The work is complete, evidence is present, and review can focus on correctness. |
| `ready_with_risks` | The work is ready, but a reviewer should confirm the stated residual risks. |
| `needs_investigation` | The status is incomplete or ambiguous, so a human should resolve the open questions first. |
| `blocked` | A hard blocker exists and review should stop until it is resolved. |

## What to Check Next

- If `Recommendation` is `ready_for_review`, scan `Decision Drivers` for any remaining caveats and then inspect `Evidence` if you need detail.
- If `Recommendation` is `ready_with_risks`, read the `Residual Risk` signal first.
- If `Recommendation` is `needs_investigation`, read `Verification`, `Unknowns`, and `Acceptance` before making a merge decision.
- If `Recommendation` is `blocked`, stop at `Decision Drivers`; the status is already telling you not to proceed.
- If `Scenario Coverage` is `incomplete`, decide whether the Work Item has explicit `ready_with_risks` acknowledgement plus `residualRisks`, `followUps`, or `unverifiedScenarios`. If it does, the task may still be reviewable with risks; if it does not, treat the missing coverage as investigation work.
- If the Preflight Review is `needs_human_confirmation` or `not_ready`, pause implementation and report the review to the user before continuing, even if Cockpit Status is otherwise visible and readable.

## Reviewer-Facing Examples

These examples use the same structure as the generated status file.

### 1. Clean Ready

```text
Recommendation: ready_for_review
Governance Signals:
- Intent: resolved
- Acceptance: complete
- Unknowns: resolved
- Verification: passed
- Guidelines: satisfied
- Checkpoints: complete
- Residual Risk: low
- Scenario Coverage: not_required

Decision Drivers:
- none
```

Use this when the task is complete, the checks passed, and there is no meaningful residual risk.

### 2. Ready With Medium Residual Risk

```text
Recommendation: ready_with_risks
Governance Signals:
- Intent: resolved
- Acceptance: complete
- Unknowns: resolved
- Verification: passed
- Guidelines: satisfied
- Checkpoints: complete
- Residual Risk: medium
- Scenario Coverage: complete

Decision Drivers:
- highest residual risk: medium
```

Use this when the implementation is ready, but the reviewer should consciously accept the stated risk.

### 3. Scenario Coverage Incomplete but Ready With Risks

```text
Recommendation: ready_with_risks
Governance Signals:
- Intent: resolved
- Acceptance: complete
- Unknowns: resolved
- Verification: passed
- Scenario Coverage: incomplete
- Guidelines: satisfied
- Checkpoints: complete
- Residual Risk: medium

Decision Drivers:
- required scenario unverified: GitHub Actions checkout extraheader reuse
```

Use this when the task is ready for review, but one or more required scenarios remain unverified and the Summary explicitly records the residual risk, follow-up path, or unverified scenario list.

### 4. Missing Verification

```text
Recommendation: needs_investigation
Governance Signals:
- Intent: resolved
- Acceptance: incomplete
- Unknowns: resolved
- Verification: incomplete
- Guidelines: satisfied
- Checkpoints: incomplete
- Residual Risk: low
- Scenario Coverage: not_required

Decision Drivers:
- required verification incomplete (missing: aiSummary; not_run: aiStatusCheck)
```

Use this when required checks are still missing or have not been recorded as passed.

### 5. Unknowns Remaining

```text
Recommendation: needs_investigation
Governance Signals:
- Intent: resolved
- Acceptance: incomplete
- Unknowns: open
- Verification: passed
- Guidelines: satisfied
- Checkpoints: complete
- Residual Risk: low
- Scenario Coverage: not_required

Decision Drivers:
- contract unknowns: 1
- summary unknownsRemaining: 2
```

Use this when the Work Item still has open questions and the reviewer should not treat it as finished.

### 6. Intent Unresolved

```text
Recommendation: needs_investigation
Governance Signals:
- Intent: unresolved
- Acceptance: incomplete
- Unknowns: resolved
- Verification: passed
- Guidelines: satisfied
- Checkpoints: complete
- Residual Risk: low
- Scenario Coverage: not_required

Decision Drivers:
- intent alignment unresolved for: problem, constraints
```

Use this when the task has a meaningful intent but the Summary does not yet prove that the declared intent was satisfied.

## Stabilization Rule

V2.5 stabilization should validate these examples against real Work Items before V3 is considered.
If the model starts needing more fields or longer output to explain itself, that is a signal to refine the review process, not to expand the status surface.
