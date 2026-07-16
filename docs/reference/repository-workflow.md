---
author: Ray
title: "Repository Workflow"
description: Repository-role-aware Work Item, branch, and pull or merge request workflow.
keywords:
  - ai-cockpit
  - work-item
  - branch
  - pull-request
  - adopter-project
---

# Repository Workflow
AI Cockpit uses one Work Item, one dedicated work branch, and one pull or merge request as its default review unit.
## Template repository
Template maintenance uses the template repository's protected default branch:

```text
latest origin/main → Work Item branch → one PR → merge → cleanup
```

The complete closure order is:

```text
latest remote base → dedicated Work Item branch → finish/archive → push → PR → merge → ai-close-work-item → synchronized clean base
```

Do not merge the Work Item branch into local `main` before opening or merging the PR. That makes local `main` appear ahead of `origin/main` and bypasses the review unit. Do not delete the Work Item branch as part of PR merge before running `ai-close-work-item`; closure needs the merged branch identity to verify ownership before it synchronizes the base and removes both branch copies.
## Adopter project
An adopter project keeps its own Git history and branch policy:

1. Identify the remote and platform-configured default branch.
2. Fetch it and create the work branch from its latest default-branch commit.
3. Record `baseRemote`, `baseBranch`, and `baseCommit` in the Contract.
4. Use a published release tag for installation or upgrade, not a moving template branch.
5. Open one adopter-project PR, then delete the remote and local branch after merge.

The remote does not have to be named `origin`, and the default branch does not have to be `main`.

## Lifecycle closure

After the Work Item is archived and its PR is merged, run `make ai-close-work-item TASK=<task>`. The command discovers the repository base remote and default branch, verifies the current branch and PR mapping, switches to the base branch, fetches, and synchronizes with `git merge --ff-only`. Only then does it delete the local work branch and remote work branch. It finishes by verifying a clean worktree and identical local/remote base commits.

The command is fail closed: an unmerged PR, inconsistent archived evidence, dirty state, non-fast-forward update, branch mismatch, deletion failure, or final synchronization mismatch prevents a successful closed result. The remote deletion is deliberately last so a failure leaves the local base branch safe for recovery.
## Installation and upgrade boundary
The template repository publishes a release; the adopter project consumes it and owns the resulting changes:

- template release preparation belongs to a template Work Item and template PR;
- adoption or upgrade belongs to an adopter-project Work Item and adopter-project PR;
- the two PRs have separate branches, base commits, reviews, and cleanup;
- record the release tag and source identity in the adopter Work Item.

Platform-specific facts such as PR number, approval state, and merge queue state belong to the hosting platform adapter. Repository-local Contract evidence records the branch base and source release without pretending to prove platform identity.
