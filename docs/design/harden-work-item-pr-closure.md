---
author: Codex
title: "Harden Work Item PR Closure Design"
description: Design for enforcing the Work Item branch, PR merge, and lifecycle closure order.
keywords:
  - ai-cockpit
  - work-item
  - pull-request
  - lifecycle-closure
---

# Design: Harden Work Item PR Closure

## Problem

The repository's intended lifecycle is easy to violate at the handoff between PR merge and local cleanup. A PR merge can remove the feature branch before `make ai-close-work-item` can identify it, and a local merge into `main` can leave local `main` ahead of `origin/main`. The result is an incomplete lifecycle even when the PR itself is merged.

## Decision

Make the lifecycle explicit and enforce the earliest unsafe transition:

1. Start from the latest remote base and create one dedicated Work Item branch.
2. Finish and archive the Work Item on that branch.
3. Push the branch and create the PR.
4. Merge the PR without deleting the Work Item branch before local closure.
5. Run `make ai-close-work-item TASK=<task>` while the merged Work Item branch is still identifiable. Closure verifies the archived evidence and merged PR, synchronizes the local base fast-forward-only with its remote, then deletes local and remote Work Item branches.

`ai-finish` will refuse to run on the discovered repository base branch. `ai-close-work-item` will retain fail-closed behavior and give an actionable message if it is invoked from the base branch or after the Work Item branch was removed. The rules remain provider-neutral and do not automate PR creation or merging.

## Verification

- Unit/regression coverage for finish on base versus feature branches.
- Lifecycle closure coverage for the base-branch error and the normal merged-PR path.
- Documentation checks and the repository's required AI checks.
