---
author: Codex
title: "Decouple Immutable Archive History from Complexity Thresholds"
description: Design for keeping historical Work Item evidence auditable without blocking current work on cumulative archive count.
keywords:
  - governance
  - archive
  - complexity
---

# Decouple Immutable Archive History from Complexity Thresholds

## Problem

The governance complexity checker currently treats cumulative archived Contract and Summary counts as blocking limits. Because archived evidence is immutable and every completed Work Item adds another pair, the check is guaranteed to fail again as the repository grows. Historical evidence is valid past context and should not determine whether an unrelated current Work Item can proceed.

## Design

Keep archive Contract/Summary counts in the generated complexity report as observational metrics, but remove them from the blocking policy limits. Keep archive integrity as a blocking concern: Contract/Summary pairing, archive index shape, and index path existence must continue to fail the check when invalid.

The current PR remains responsible for the relationship between new work and archive evidence. Existing PR ownership validation continues to inspect changed archive pairs and must not be weakened or broadened by this change.

Non-archive complexity limits for tracked files, Python lines, and Markdown lines remain unchanged.

## Data flow

```text
archive files ──> archive metrics ──> report only
archive files ──> pairing/index validation ──> blocking integrity result
current PR diff ──> check-ai-pr ──> blocking ownership result
live repository files ──> complexity limits ──> blocking complexity result
```

## Testing

Add a regression case proving that archive totals above the former limit pass when archive integrity is valid. Retain and run the existing failure cases for missing pairs and dangling index paths. Run the project quality suite and the required AI Cockpit checks.

## Non-goals

- Do not delete, rewrite, compact, or relocate historical archive evidence.
- Do not change current-PR archive ownership rules.
- Do not change tracked-file, Python-line, or Markdown-line thresholds.
- Do not introduce external archive storage in this Work Item.
