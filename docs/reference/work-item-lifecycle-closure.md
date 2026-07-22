---
author: Ray
title: "Work Item Lifecycle Closure"
description: Fail-closed closure protocol for returning a repository to the next-task-ready state.
keywords:
  - ai-cockpit
  - work-item
  - lifecycle
  - closure
  - cleanup
---

# Work Item Lifecycle Closure

Closure means the repository is ready to begin the next Work Item. It is not equivalent to deleting a branch.

Run:

```sh
make ai-close-work-item TASK=<task>
```

The command requires the Work Item Contract and Summary to be archived, no active Work Item evidence, a consistent no-active Cockpit Status, and a merged PR whose head branch is the current Work Item branch.

Its ordered protocol is:

```text
verify evidence and merged PR
→ switch to discovered base branch
→ fetch remote
→ fast-forward base branch
→ verify local base equals remote base
→ delete local Work Item branch
→ request remote Work Item branch deletion
→ refresh remote refs and verify the Work Item branch is absent
→ verify clean repository and synchronized base
→ report ready for next Work Item
```

The command stops at the first unverified failure. It never deletes the remote branch before local base safety is established, never uses an implicit merge commit, and never reports `closed` unless the final remote-ref check proves the branch is absent. If GitHub or another platform has already deleted the branch, the redundant delete request may return non-zero; after `fetch --prune`, a verified absent remote ref is treated as the idempotent success state. A branch that still exists, or a remote state that cannot be verified, remains fail-closed. Squash and rebase PRs are supported because the merged PR, rather than local ancestry, authorizes deletion of the source branch.

`make ai-finish TASK=<task>` is an archive milestone, not lifecycle closure. Its successful output explicitly directs the operator to push the Work Item branch, open and merge the PR, and then run `ai-close-work-item`. Historical local branches or detached worktrees outside the current Work Item are not deleted automatically because their ownership cannot be established safely from a branch name alone; audit and remove them only with explicit operator authorization.

Archived evidence has one immutable root: `archive-manifest.json` is generated only after the Contract and Summary are frozen, and records their SHA-256 digests. The Summary does not hash itself, and generated `current_status.md` is excluded from this chain. The archive index records the manifest path and digest; records predating this protocol remain readable as legacy evidence.

The repository's remote name and default branch are discovered from Git's remote HEAD. Adopter projects therefore do not need to use `origin/main`.
