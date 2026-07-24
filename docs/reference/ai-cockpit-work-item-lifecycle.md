---
author: Ray
title: AI Cockpit Work Item Lifecycle
description: Deterministic serial execution, budget, and release-evidence rules for governed Work Items.
---

# AI Cockpit Work Item Lifecycle

The default execution unit is one Work Item, one dedicated branch, and one PR. Work Items in a plan are executed serially:

```text
remote base → Contract/Preflight → dedicated branch → implement → ai-finish/archive
  → push → PR/review → merge → ai-close-work-item → synchronize and clean base
  → next Work Item
```

The next Work Item must not start until the predecessor has evidence for all of the following: PR merged, archive succeeded, local branch deleted, remote branch deleted, and local base synchronized with the remote base. A successor Contract may record this evidence in `predecessorWorkItem`; `make check-ai-serial-order` fails closed when any field is absent or false.

## Contract readiness

Active v2 code Contracts must contain concrete problem, constraints, rationale, sources, acceptance, and verification content. Generic starter phrases are rejected by the Contract check before implementation. If Preflight reports `needs_human_confirmation` or `not_ready`, stop and report the reason; do not continue by treating advisory output as authorization.

## Complexity budget

Before implementation, estimate expected changes in the Contract's `budgetImpact`. At finish, `make check-ai-budget-impact` compares the generated complexity report with `.ai/guards/governance_complexity_policy.yaml`. An overrun is permitted only when the Contract explicitly records approval, a repayment Work Item, and repayment records. A separate budget-repair Work Item/PR is the appropriate repayment path when the current Work Item cannot repay its own increase.

## Release evidence states

Release evidence uses three distinct states:

- Historical: an existing archived Work Item or prior release record; preserve it as evidence and do not rewrite it.
- Candidate: a release commit/tag and its generated artifacts are prepared, but publication and source binding are not yet proven.
- Published: the public tag, source commit, release assets, checksums, SBOM, provenance, and release-state checks all point to the same source-bound release.

Do not report a candidate as published. `check-release-distribution` remains the source-bound verification for public release evidence.

## Closure rule

Only after the PR is merged and the Work Item is archived may `make ai-close-work-item TASK=<task>` run. The command owns branch deletion and must fail closed on any lifecycle mismatch. After closure, verify the local base equals the remote base and only then begin the next serial Work Item.
## Preflight hard gates before PR and release

After `make ai-finish TASK=<task>` archives the Work Item, commit the complete
Work Item bundle, then run `make check-ai-pr AI_BASE_COMMIT=<latest-default-branch-sha>`.
Do not run the aggregate PR check against an uncommitted archive or generated
release evidence. Independent review must finish while evidence is active;
post-archive fixes require a fresh Work Item and replacement PR. The order is:

```text
independent review → ai-finish/archive → commit bundle → check-ai-pr → push → PR
```

This gate first runs the project formatter and, when the governance script and policy
are installed, the governance complexity/budget check; only then does it validate PR
ownership. This catches formatting drift and budget overflow before remote CI.
The PR must contain exactly one newly maintained Work Item and must be based on the
latest remote default branch; a branch derived from another unmerged Work Item is
invalid even when its tests pass.

When CI or PR checks block a change, pause before retrying. Perform a process-root-
cause review for missing preflight gates, wrong ordering, late formatter or budget
checks, template/adopter boundary errors, and source-bound evidence design. If the
failure is preventable in the workflow, open and complete a corrective Work Item
that adds an executable fail-closed gate before resuming the original operation.

Before release evidence is generated, run
`make finalize-release-freeze-premerge TASK=<task>` on the dedicated Work Item
branch after `ai-finish` has archived the Work Item and before committing the
release metadata. This is the only supported premerge freeze writer for a release
preparation PR: it requires the archived Work Item evidence, a clean branch, and
source-bound candidate metadata. Its canonical `sourceTree` and `archiveSha256`
are calculated from the clean candidate branch `HEAD`. The controlled
`SOURCE_COMMIT` reference is retained separately so the hosted release workflow
can resolve the exact merged default-branch identity. Both `.ai/work-items/active` and
`.ai/work-items/archive` are export-ignored, so moving evidence during Finish does
not change canonical content. After merge, the hosted detached checkout must
regenerate the same tree and archive or stop before tag mutation. Then run
`make check-release-preflight`; it fails closed when lifecycle evidence is absent
or inconsistent, archive policy blocks, or regenerated content differs.

```json
{
  "state": "frozen",
  "sourceTree": "<exact-default-branch-tree-sha>",
  "archiveSha256": "<regenerated-canonical-archive-sha256>",
  "lifecycle": {
    "state": "closed_and_synchronized",
    "command": "make ai-close-work-item",
    "baseCommit": "<exact-default-branch-tree-sha>",
    "worktreeClean": true
  }
}
```

After the marker and release metadata are bound, no new Work Item may be archived
until publication is complete. If any check fails, return to the candidate phase
and regenerate the source-bound evidence.

Template and adopter boundary: template-maintenance branches use the template
repository's `project-format-check` and governance policy from the latest template
default branch. An installed adopter uses its own configured formatter, remote
default branch, base commit, and governance policy; it must not copy the template's
absolute line or archive budgets.
