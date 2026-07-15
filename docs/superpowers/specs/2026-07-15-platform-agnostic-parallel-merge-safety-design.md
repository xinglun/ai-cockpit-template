---
author: Ray
title: "Platform-Agnostic Parallel Merge Safety Design"
description: "GitHub、GitLab Merge Trains 与 GitLab Free 原生 Git 兼容门禁的并行合并安全设计。"
keywords:
  - parallel-development
  - merge-queue
  - merge-train
  - gitlab-free
  - candidate-verification
  - hci
---

# Platform-Agnostic Parallel Merge Safety Design

## Status

This document is an approved design, not a statement that the described runtime, installer, or CI integration is already implemented.

## Goal

Enable teams to develop independent AI Cockpit Work Items in parallel while preserving evidence-backed merge safety across GitHub, GitLab Premium or Ultimate, and GitLab Free.

The design keeps Git and the hosting platform responsible for branch topology, ordering, conflict resolution, and aggregation. AI Cockpit remains responsible for determining whether the exact candidate tree being considered for merge has complete project and governance evidence.

## Audience

This document is for AI Cockpit maintainers and CI adapter implementers. It defines the safety properties, platform boundaries, evidence strength, and failure behavior that later implementation Work Items must preserve. Adopters should receive shorter platform-specific setup guidance generated from this design rather than being expected to implement the protocol directly.

## North Star and HCI Constraint

The North Star is Calibrated Human-Agent Trust. Architecture boundaries support that mission; they are not goals by themselves.

When a hosting platform lacks a safe candidate-merge facility, a compatibility adapter should absorb that capability gap with native Git and CI controls when safety can be established. The adopter should not be forced to accept weaker evidence or purchase a higher hosting tier solely to preserve an abstractly pure AI Cockpit Core boundary.

This does not authorize hidden emulation or unsupported claims. The system must expose which candidate mode was used, what freshness guarantees were established, and when only head-branch validation is available.

## Decisions

1. One Work Item maps to one branch and one pull or merge request.
2. Git and the hosting platform own aggregation and merge ordering.
3. AI Cockpit Core receives a candidate tree and a target base commit; it does not own queue state.
4. Platform-generated candidates are preferred.
5. GitLab Free receives a native-Git synthetic candidate plus a serialized final merge gate.
6. Head-only validation is supported as a diagnostic fallback but is not parallel merge safety.
7. Candidate freshness failures are fail-closed.

## Non-Goals

- Implementing a branch graph, queue scheduler, or cross-branch lock service inside AI Cockpit Core.
- Adding GitHub- or GitLab-specific fields to Work Item Contract, Summary, Archive, or Cockpit Status schemas.
- Predicting semantic conflicts without building and testing a candidate tree.
- Replacing protected branches, platform approvals, or trusted human review.
- Storing automation credentials, access tokens, or platform secrets in the repository.
- Implementing the design in this documentation Work Item.

## Core Verification Contract

This document uses **Core** as shorthand for **AI Cockpit Core**.

All platform adapters normalize their environment into the same Core contract:

```text
checked-out HEAD = exact candidate tree to evaluate
AI_BASE_COMMIT   = target-branch commit against which the candidate is audited
```

Core then executes the existing aggregate gate:

```sh
make ai-pre-merge AI_BASE_COMMIT="$AI_BASE_COMMIT"
```

The candidate mode is platform-neutral observation metadata:

```text
native     platform generated the candidate tree
synthetic  the compatibility adapter generated it with native Git
head_only  no target-integrated candidate was established
```

Candidate mode does not alter scope or ownership semantics. It controls how strongly the result may be described. Only `native` and `synthetic` results with verified freshness may support a parallel-merge-safe conclusion. A `head_only` result must remain visibly incomplete.

## Responsibility Boundaries

| Layer | Responsibility |
| --- | --- |
| Developer branch | Contains one Work Item and its implementation commits. |
| Pull or merge request | Carries review, approval, and platform identity. |
| Git | Builds candidate trees and detects textual merge conflicts. |
| Hosting platform | Provides native queues when available, protects the target branch, and performs the final merge. |
| Platform adapter | Resolves platform events into candidate/base facts or safely constructs a missing candidate. |
| Project verification | Detects build, test, lint, and semantic integration failures. |
| AI Cockpit Core | Validates scope, archive ownership, evidence, status consistency, and the complete candidate diff. |
| Human reviewer | Accepts residual risk and controls trusted approval boundaries. |

Core must not read platform APIs merely to discover queue position or maintain cross-request state. Platform-specific event parsing, credentials, and merge execution stay in adapters and installation templates.

## Native Platform Adapters

A target-integrated candidate is not automatically fresh enough to merge. Native adapters must establish both candidate construction and final freshness:

| Platform mode | Candidate includes target | Final freshness mechanism | Permitted conclusion |
| --- | --- | --- | --- |
| GitHub pull-request merge ref only | yes, at pipeline creation | none unless branch rules require an updated branch | candidate tested; parallel merge safety not established |
| GitHub Merge Queue `merge_group` | yes | queue rebuilds and checks the merge-group SHA | parallel merge protection established |
| GitLab detached MR pipeline | no | none | head-only branch validation |
| GitLab merged results pipeline only | yes, at pipeline creation | none unless project policy rejects stale results | candidate tested; parallel merge safety not established |
| GitLab Merge Train | yes | train rebuilds cumulative candidates after queue changes | parallel merge protection established |
| GitLab Free compatibility gate | yes | serialized gate plus atomic fast-forward target update | parallel merge protection established for the governed merge path |

If platform policy or event evidence cannot prove the listed freshness mechanism, the adapter must downgrade the result instead of inferring safety from a green pipeline.

### GitHub

Normal pull-request validation runs against the pull request candidate available to GitHub Actions. When Merge Queue is enabled, required workflows also listen to `merge_group` with `checks_requested` and run against the merge-group SHA.

The adapter resolves the target base from the event payload or fetched target ref and passes it as `AI_BASE_COMMIT`. The merge-group checkout is already the candidate tree. AI Cockpit audits every changed path and every newly introduced archive pair in that complete candidate diff; it does not reproduce the queue's ordering.

### GitLab Premium and Ultimate

Merged results pipelines and Merge Trains provide target-integrated candidate commits. The adapter recognizes `CI_MERGE_REQUEST_EVENT_TYPE` values such as `merged_result` and `merge_train`, uses the platform-provided target SHA as the base, and treats the checked-out internal merged result commit as the candidate.

When several merge requests are on a train, GitLab owns the cumulative ordering. AI Cockpit sees one candidate tree containing the relevant changes and validates its aggregate evidence.

## GitLab Free Compatibility Gate

GitLab Free has merge-request pipelines and CI resource groups but does not provide Merge Trains. A normal merge-request pipeline validates the source branch, not necessarily the result of merging it into the current target branch. Therefore a green source pipeline alone cannot establish parallel merge safety.

The compatibility flow has two phases.

### Phase 1: Parallel Feedback

Every merge request runs formatting, unit tests, static analysis, and Work Item checks in parallel. This preserves fast developer feedback and rejects incomplete evidence before the request reaches the final gate.

Phase 1 may report that the branch itself is healthy. It does not claim that the request is safe to merge with the latest target.

### Phase 2: Trusted Serialized Candidate and Merge Gate

The final gate runs in a coordinator pipeline whose CI configuration is loaded from the protected target branch, not from the untrusted merge-request source branch. The merge-request pipeline may request coordination only after Phase 1 succeeds; it never receives the protected automation credential. The coordinator treats the merge request IID, project path, and source SHA as untrusted inputs and resolves authoritative state through Git and the GitLab API.

The coordinator job uses a target-specific GitLab `resource_group`, for example `ai-cockpit-merge-main`. The lock covers candidate construction, full verification, freshness revalidation, and the atomic protected-target Git push. Serialization is the safety property; `oldest_first` is recommended for fairness but is not required for correctness.

The gate performs these steps:

1. Read the merge request's current source SHA and target branch through the GitLab API.
2. Fetch the exact source SHA and the latest protected target SHA without accepting ambient `GIT_DIR`, `GIT_WORK_TREE`, or caller-provided repository state.
3. Create an isolated temporary worktree at the target SHA.
4. Use native `git merge` to combine the source SHA with the target SHA.
5. Fail immediately on textual conflicts and report the conflicting paths.
6. Create a temporary local candidate commit. It remains unreferenced remotely until verification succeeds; after a successful atomic push, this exact commit becomes target-branch history.
7. Run `make ai-pre-merge` with the fetched target SHA as `AI_BASE_COMMIT` against the temporary local candidate commit.
8. Query the merge request's authoritative eligibility state. Require it to remain open, non-draft, and backed by the successful required source pipeline for the exact source SHA. If the project has configured approval, unresolved-discussion, or CODEOWNERS-related gates that the installed GitLab API exposes, validate those gates too. A configured gate that cannot be established fails closed.
9. Re-read both source and target SHAs after verification and eligibility validation.
10. If either SHA changed, discard the evidence and restart or requeue the gate; never reuse the stale result.
11. If both SHAs are unchanged, push the verified candidate commit to the protected target ref with a normal fast-forward Git push. If the target changed, Git rejects the non-fast-forward update and the candidate is requeued.
12. Query the GitLab merge request after the ref update and reconcile platform bookkeeping when required; bookkeeping failure is reported separately and never changes which commit was verified and pushed.
13. Record the candidate mode, source SHA, target SHA, candidate SHA, verification result, eligibility snapshot, and ref-update response as CI evidence.
14. Remove the temporary worktree on success, failure, or cancellation. Failed candidates remain unreachable local objects and may be pruned normally; a successfully pushed candidate is retained as target-branch history.

The target branch must reject direct pushes and merges from non-administrative identities that are outside this gate. All governed merge requests targeting the branch must use the same resource group. A dedicated automation user performs the protected fast-forward push with a GitLab Free-compatible credential, such as a protected personal access token with the minimum repository-write scope accepted by the installed GitLab instance. The credential is available only to the protected target-branch coordinator and protected runners; it is never exposed to source-branch-controlled CI. The installer supplies configuration guidance and placeholders but never creates, copies, prints, or stores the credential.

The final normal Git push is the concurrency-correctness boundary. The candidate commit is a descendant of the exact target SHA used for verification, so a concurrent target update makes the push non-fast-forward and causes Git to reject it. The resource group avoids waste and provides an explainable order; the atomic ref update prevents correctness from depending on timing between a CI job completing and a later platform merge action. Protected branches, exact-SHA pipeline evidence, and explicit validation of applicable merge-request eligibility gates complete the governed automation boundary. Human-review policy is a separate concern from parallel-merge correctness and is enforced only when the installed project configures such a gate and the coordinator can establish its authoritative state.

GitLab Free commonly grants protected-branch merge or push authority by role rather than exclusively to one bot. Maintainer or administrator bypass therefore remains an explicit trusted-human boundary. The compatibility mode establishes safety for the required governed path; it does not claim that privileged humans, compromised runners, or instance administrators are technically unable to bypass policy.

## Evidence Strength and User-Facing State

The verification result should expose capability rather than platform jargon:

| Candidate mode | Candidate includes target | Freshness established | Permitted conclusion |
| --- | --- | --- | --- |
| `native` | yes | yes | parallel merge protection established |
| `synthetic` | yes | yes | parallel merge protection established for the governed compatibility path |
| `head_only` | no | no | branch checks passed; parallel merge safety not established |

Recommended human-facing output:

```text
Parallel merge protection: established
Candidate generation: Git compatibility mode
Platform-native queue: unavailable
Safety fallback: active
```

If configuration is incomplete, report the missing action directly:

```text
Parallel merge protection: not established
Reason: target branch permits merges outside the serialized gate
Next action: protect main and require the ai-cockpit-merge-main job
```

Missing or weaker evidence must not be compressed into `ready_for_merge`.

## Failure Semantics

| Failure | Required behavior |
| --- | --- |
| Native or synthetic merge conflict | Fail closed and report conflicting paths. |
| Source SHA changes during verification | Discard evidence and requeue. |
| Target SHA changes during verification | Discard evidence and rebuild against the new target. |
| Project quality check fails | Do not merge; preserve the failing check evidence. |
| AI ownership or archive check fails | Do not merge; report unowned, ambiguous, or out-of-scope paths. |
| Automation credential is absent or insufficient | Do not downgrade to an unprotected merge; report configuration guidance. |
| Coordinator runs from source-controlled or unprotected CI context | Refuse credential access and report that trusted candidate execution is not established. |
| Non-administrative identities can bypass the required gate | Report that the governed path is not enforced and refuse the synthetic safety claim. |
| Required merge-request eligibility state is false, stale, or unavailable | Do not push; report the specific draft, pipeline, approval, discussion, or policy evidence that is missing. |
| Atomic target push is rejected | Treat the candidate as stale, fetch the new target, and requeue without force-pushing. |
| Candidate cleanup fails | Fail the job and report the temporary path without exposing credentials. |
| Platform API is unavailable | Preserve the last known evidence as incomplete; do not merge. |

Retries must be bounded and visible. A repeatedly moving target should return a stale-candidate result and re-enter the normal CI queue rather than loop indefinitely.

## Security and Trust Boundaries

- Candidate construction runs in an isolated temporary worktree or disposable clone.
- Ambient Git repository variables are removed before every public Git operation.
- All fetched SHAs are resolved and recorded explicitly.
- The automation credential is supplied by protected CI secret storage only to a target-branch-controlled coordinator and is never written to generated evidence.
- Fork-originated requests do not receive protected automation credentials.
- Merge-request-controlled CI files cannot modify the coordinator job that receives protected credentials.
- When approval, discussion, or CODEOWNERS-related gates are configured, the coordinator reads their authoritative state from GitLab and fails closed if it cannot bind that state to the current request and source SHA.
- CI records are execution evidence, not tamper-proof attestations.
- Maintainer or administrator bypass, compromised runners, and malicious repository policy changes remain external trust boundaries.

## Installation and Capability Detection

Installation should not silently infer a guarantee from a remote hostname. Doctor or onboarding may detect likely platform facts, but edition, feature availability, branch protection, runner permissions, and credentials must be validated from evidence or left unknown.

The installed project selects one of these profiles:

- GitHub native candidate verification.
- GitLab native merged results or merge-train verification.
- GitLab synthetic compatibility gate.
- Generic explicit base/head integration.
- Head-only diagnostic mode.

The same project may move from synthetic to native mode after a GitLab edition or policy change without changing Work Item schemas.

### Generic Explicit Base/Head Integration

The generic profile is for CI systems that can check out or construct a candidate but do not have a bundled adapter. The caller must provide:

- an exact candidate commit checked out as `HEAD`;
- the exact target commit as `AI_BASE_COMMIT`;
- candidate mode (`native`, `synthetic`, or `head_only`);
- evidence of how source and target freshness are checked;
- the atomic mechanism that prevents a different target state from being merged after verification.

Core validates the candidate diff but does not trust caller labels alone. Without a target-integrated candidate and an atomic platform merge or Git ref update tied to the verified target, the generic profile is limited to a diagnostic conclusion. Invalid commits, unreachable bases, dirty candidate trees, missing freshness evidence, or an unspecified final update mechanism fail closed.

## Testing Strategy for a Future Implementation

### Core tests

- The same candidate/base pair produces identical ownership conclusions regardless of platform adapter.
- Multiple valid archive pairs in one candidate pass aggregate PR ownership.
- Unowned, ambiguous, approval-required, and out-of-scope paths fail closed.
- Head-only evidence cannot produce a parallel-merge-safe recommendation.

### Adapter tests

- GitHub pull-request and merge-group fixtures resolve the correct candidate and base.
- GitLab detached, merged results, and merge-train fixtures select the correct capability mode.
- Platform-specific environment variables do not leak into Contract, Summary, or Archive schemas.

### GitLab Free integration tests

- Two independent merge requests run Phase 1 concurrently and pass through the final resource group one at a time.
- The second candidate is rebuilt against the target after the first request merges.
- Textual conflicts fail before project verification.
- A semantic incompatibility that merges textually is caught by project tests.
- A source push during verification invalidates the candidate.
- A target update during verification invalidates the candidate.
- A target update immediately before the final push causes a non-fast-forward rejection and requeue.
- Missing credentials, unprotected target branches, and non-administrative bypass paths prevent the governed-path safety claim.
- A source-branch pipeline cannot read or alter the protected coordinator credential or configuration.
- The temporary worktree is removed on success, failure, timeout, and cancellation.
- Logs and generated evidence redact automation credentials and private remote fragments.

### End-to-end acceptance

- GitHub Merge Queue, GitLab Merge Trains, and GitLab Free compatibility mode all invoke the same Core pre-merge gate.
- Each mode produces an explainable candidate-strength result.
- The governed merge path never updates its target branch with a candidate that did not pass verification against the target state used for that ref update.

## Rollout Sequence

1. Define the platform-neutral candidate evidence model and Core command contract.
2. Add GitHub pull-request and merge-group adapters.
3. Add GitLab merged results and merge-train adapters.
4. Add the GitLab Free isolated candidate builder.
5. Add the serialized protected merge gate and credential guidance.
6. Add installer profiles, Doctor capability reporting, and adoption documentation.
7. Verify all modes with disposable repositories before describing the capability as released.

Each implementation phase requires its own Work Item Contract and verification evidence. The GitLab Free merge identity and protected-branch policy require explicit adopter configuration and cannot be silently approved by the installer.

## References

- [GitHub: Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [GitHub Actions: `merge_group` event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group)
- [GitLab: Merge request pipelines](https://docs.gitlab.com/ci/pipelines/merge_request_pipelines/)
- [GitLab: Merge trains](https://docs.gitlab.com/ci/pipelines/merge_trains/)
- [GitLab: Predefined merge request variables](https://docs.gitlab.com/ci/variables/predefined_variables/)
- [GitLab: Resource groups](https://docs.gitlab.com/ci/resource_groups/)
- [GitLab: Merge requests API](https://docs.gitlab.com/api/merge_requests/)
