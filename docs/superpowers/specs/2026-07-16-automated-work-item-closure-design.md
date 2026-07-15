---
author: Ray
title: "Automated Work Item Lifecycle Closure Design"
description: Design options for automating post-merge Work Item cleanup without weakening local and remote safety boundaries.
keywords:
  - ai-cockpit
  - work-item
  - lifecycle
  - automation
---

# Automated Work Item Lifecycle Closure Design

## Problem and boundary

The repository currently requires a human to run `make ai-close-work-item TASK=<task>` after a PR is merged. A hosted CI/CD runner can authenticate against the remote repository, but it cannot delete a developer's local branch in an existing clone. Therefore “automatic closure” must distinguish remote cleanup from local cleanup and must not assume that an adopter uses GitHub, GitLab, or any particular remote name or default branch.

## Fixed governance threshold

The PR41-merged `main` baseline reports 721 tracked files. This Work Item adds one tracked design artifact, so `.ai/guards/governance_complexity_policy.yaml` fixes `trackedFiles` at 722 before implementation and remote checks. The archive bounds remain at 264 for Contracts and Summaries because the current main baseline is 253 each and this investigation does not archive a Work Item. A later repository-shape change must update the policy through a separate, evidence-backed Work Item rather than silently relying on a moving threshold.

## Options

### Option A: Hosted CI/CD provider adapter only

Configure a provider-specific adapter for the adopter's hosting platform. The adapter triggers on the platform's merged pull/merge request event, continues only when the request is actually merged, validates the merged request and archived evidence, then verifies or deletes the remote source branch.

This is centrally observable, but it cannot clean local branches. It also adds a destructive provider-token path and must handle provider-side auto-deletion races. The template may ship a GitHub Actions example for this repository, but the installed adopter configuration must select or implement an adapter for its actual provider.

### Option B: Local post-merge automation only

Install a repository-managed `post-merge` hook or equivalent local sync command. After a developer updates the base branch, it discovers merged Work Item PRs, verifies archive evidence, and removes matching local branches.

This can clean local branches without granting CI remote-delete permissions, but setup is per clone and it cannot guarantee that every developer has the hook installed or that remote cleanup completed.

### Option C: Coordinated hosted and local automation (recommended)

Use a provider-specific hosted merge adapter for authoritative remote verification and cleanup, and a locally installed post-merge/sync hook for local branch cleanup. Both paths use the same provider-neutral evidence and merge-identity rules. Keep `ai-close-work-item` as an explicit fail-closed recovery and audit command.

The hosted side must never assume it can mutate local clones. The local side must never delete a branch based only on its name; it must verify the corresponding PR is merged and the archived Contract/Summary evidence is valid. Both sides must treat an already-absent remote branch as an idempotent success only after final verification.

## Safety requirements for a coding phase

- Trigger only for merged PRs, never merely closed PRs.
- Verify the source branch, base branch, merge commit, and archived evidence before cleanup.
- Use least-privilege provider credentials and document branch-protection or protected-branch interactions.
- Make remote deletion idempotent and preserve fail-closed behavior for unverifiable state.
- Make local cleanup opt-in through installation/configuration and retain a manual recovery path.
- Add dry-run and audit output before enabling destructive automation by default.
- Test provider-side auto-deletion, unmerged/closed PRs, missing evidence, branch-name mismatch, and local clones without the hook.

## CI/CD execution monitoring

Automation must treat CI/CD execution as an evidence-producing stage, not as a fire-and-forget trigger. The core protocol is provider-neutral; each adapter maps its platform's request, pipeline, job, status, URL, and retry concepts into the protocol:

- Correlate checks and pipeline/job runs by the merged request head SHA, not only by branch name.
- Aggregate required checks into an explicit `pending`, `passed`, or `failed` closure gate.
- Do not delete a remote branch or report closure while any required check is pending or failed.
- On failure, retain the provider run URL, failed job name, and concise log diagnosis in the request or Work Item evidence.
- Distinguish evidence failures (for example, stale archived Contract hashes) from transient runner failures and keep both visible to reviewers.
- Re-evaluate after a retry or corrective commit; never turn a previous failure into success based on stale status.

For this template repository, GitHub Actions is one concrete adapter and its checks are monitored through the GitHub pull-request/check-run APIs. This implementation detail must remain in template-maintainer documentation and must not be copied into adopter contracts as a universal requirement. An adopter on GitLab must use a GitLab CI/Merge Request adapter; another provider must either provide a conforming adapter or remain in manual, fail-closed mode. Unknown provider capability, missing correlation data, or unobservable required checks must block automated closure.

## Recommendation

Proceed with Option C as a separate coding Work Item after review. The first implementation slice should establish a read-only/dry-run merged-request verifier, a provider-neutral CI/CD result monitor with a GitHub Actions adapter for this template repository, and a local cleanup discovery command; destructive deletion should be enabled only after those evidence paths are independently verified. Adopter installation must detect or explicitly configure the provider adapter and must not install GitHub-specific automation into a GitLab project.
