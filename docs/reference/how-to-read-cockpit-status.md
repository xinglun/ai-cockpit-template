---
author: Ray
title: "How to Read Cockpit Status"
description: Reviewer-facing guide to interpreting AI Cockpit current_status.md during V2.5 stabilization.
keywords:
  - ai-cockpit
  - cockpit-status
  - reviewer-guide
  - release-hardening
  - v2.5
---

# How to Read Cockpit Status

This page explains how to read the generated Cockpit Status during V2.5 stabilization and release hardening.
It is written for reviewers, maintainers, and approvers who want the shortest path from status to decision.

## Read Order

Start with these fields in order:

1. `Recommendation`
2. `Decision Drivers`
3. `Governance Signals`
4. `Evidence`

`Recommendation` gives the decision state. `Decision Drivers` explains why that state was chosen.
`Governance Signals` show the compressed judgment, and `Evidence` points back to the repository truth.

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

Decision Drivers:
- highest residual risk: medium
```

Use this when the implementation is ready, but the reviewer should consciously accept the stated risk.

### 3. Missing Verification

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

Decision Drivers:
- required verification incomplete (missing: aiSummary; not_run: aiStatusCheck)
```

Use this when required checks are still missing or have not been recorded as passed.

### 4. Unknowns Remaining

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

Decision Drivers:
- contract unknowns: 1
- summary unknownsRemaining: 2
```

Use this when the Work Item still has open questions and the reviewer should not treat it as finished.

### 5. Intent Unresolved

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

Decision Drivers:
- intent alignment unresolved for: problem, constraints
```

Use this when the task has a meaningful intent but the Summary does not yet prove that the declared intent was satisfied.

## Stabilization Rule

V2.5 stabilization should validate these examples against real Work Items before V3 is considered.
If the model starts needing more fields or longer output to explain itself, that is a signal to refine the review process, not to expand the status surface.
