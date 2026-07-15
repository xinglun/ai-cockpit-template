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
→ delete remote Work Item branch
→ verify clean repository and synchronized base
→ report ready for next Work Item
```

The command stops at the first failure. It never deletes the remote branch before local base safety is established, never uses an implicit merge commit, and never reports `closed` after a failed cleanup step. Squash and rebase PRs are supported because the merged PR, rather than local ancestry, authorizes deletion of the source branch.

The repository's remote name and default branch are discovered from Git's remote HEAD. Adopter projects therefore do not need to use `origin/main`.
