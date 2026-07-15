---
author: Ray
title: "Platform-Agnostic Parallel Merge Safety Design"
description: "GitHub Merge Queue 与 GitLab Merge Trains 的平台无关并行合并安全设计，并明确 GitLab Free 不对应。"
keywords:
  - parallel-development
  - merge-queue
  - merge-train
  - unsupported-platform
  - candidate-verification
  - hci
---

# Platform-Agnostic Parallel Merge Safety Design

## Status

This document is an approved design, not a statement that the described runtime, installer, or CI integration is already implemented.

## Goal

Enable teams to develop independent AI Cockpit Work Items in parallel while preserving evidence-backed merge safety through GitHub Merge Queue and, where candidate binding plus no-stale-bypass policy can be evidenced, GitLab Premium or Ultimate Merge Trains.

The design keeps Git and the hosting platform responsible for branch topology, ordering, conflict resolution, and aggregation. AI Cockpit remains responsible for determining whether the exact candidate tree being considered for merge has complete project and governance evidence.

## Audience

This document is for AI Cockpit maintainers and CI adapter implementers. It defines the safety properties, platform boundaries, evidence strength, and failure behavior that later implementation Work Items must preserve. Adopters should receive shorter platform-specific setup guidance generated from this design rather than being expected to implement the protocol directly.

## North Star and HCI Constraint

The North Star is Calibrated Human-Agent Trust. Architecture boundaries support that mission; they are not goals by themselves.

When a hosting platform lacks a safe candidate-merge facility, AI Cockpit must expose that capability gap instead of implying an equivalent guarantee. The adopter may still run head-branch diagnostics, but those checks are not parallel merge safety.

This does not authorize hidden emulation or unsupported claims. The system must expose how the candidate was constructed, what freshness guarantees were established, and when only head-branch validation is available.

## Decisions

1. One Work Item maps to one branch and one pull or merge request.
2. Git and the hosting platform own aggregation and merge ordering.
3. AI Cockpit Core receives a candidate tree and a target base commit; it does not own queue state.
4. Platform-generated, target-integrated candidates are necessary but not sufficient for a supported parallel merge safety conclusion; candidate construction and freshness are independent evidence dimensions.
5. GitLab Free does not correspond to this design's supported parallel merge safety modes.
6. GitLab Free and other platforms without a supported target-integrated candidate facility may use head-only validation as a diagnostic fallback, but that is not parallel merge safety.
7. Candidate identity, ancestry, freshness, event-correlation, or enforcement-policy failures are fail-closed.

## Non-Goals

- Implementing a branch graph, queue scheduler, or cross-branch lock service inside AI Cockpit Core.
- Adding GitHub- or GitLab-specific fields to Work Item Contract, Summary, Archive, or Cockpit Status schemas.
- Predicting semantic conflicts without building and testing a candidate tree.
- Replacing protected branches, platform approvals, or trusted human review.
- Storing automation credentials, access tokens, or platform secrets in the repository.
- Designing or implementing a synthetic GitLab Free merge coordinator.
- Implementing the design in this documentation Work Item.

## Core Verification Contract

This document uses **Core** as shorthand for **AI Cockpit Core**.

All platform adapters normalize their environment into the same Core execution contract:

```text
checked-out HEAD = exact candidate tree to evaluate
AI_BASE_COMMIT   = target-branch commit against which the candidate is audited
```

Core then executes the existing aggregate gate:

```sh
make ai-pre-merge AI_BASE_COMMIT="$AI_BASE_COMMIT"
```

The current `ai-pre-merge` command validates the checked-out tree and aggregate diff. A future adapter implementation must also emit exactly one transient `target/ai_merge_candidate_evidence.json` per run and upload it with the retained CI artifacts. It is generated evidence, never committed or hand-edited, and is not a new Contract, Summary, Archive, or Cockpit Status field.

The normative v1 JSON object has the following shape. Every listed property is required; only fields typed with `null` may be null. Timestamps use RFC 3339 UTC. Non-null SHA strings must resolve to exact commit objects rather than symbolic refs:

```text
schemaVersion: 1
platform: string
repositoryIdentity: string | null
eventIdentity: string | null
aggregateIdentity: string | null
observedSource: { requestIdentity: string, sourceSha: string } | null
candidateConstruction: target_integrated | head_only | null
candidateSha: string | null
baseSha: string | null
freshnessStatus: established | not_established
freshnessEvidence: {
  mechanism: queue_managed | train_managed | atomic_ref_update | none,
  terminalObservation: string,
  observedAt: RFC-3339-UTC string
}
policyEvidence: {
  requiredChecks: string[],
  bypassPrevention: established | not_established | unknown,
  observedAt: RFC-3339-UTC string,
  details: string[]
}
outcomeReason: string | null
coreResult: passed | failed | not_run
evidenceResult: passed | failed | incomplete
mergeSafety: established | not_established
```

Non-null identity strings are opaque, non-empty UTF-8 values. `eventIdentity` must be unique within `repositoryIdentity`, and `aggregateIdentity` names the platform-maintained merge group, train candidate, or generic candidate transaction. It—not `observedSource`—binds cumulative membership. `observedSource` records the single request/source pair when the triggering event exposes one; it is null for an aggregate event that has no single authoritative source. Adapters must not attempt to reconstruct cumulative membership from a partial list. Core audits the complete candidate tree, while the platform remains authoritative for group/train membership.

For a completed checkout, `HEAD` must equal non-null `candidateSha`; non-null `baseSha` must be bound to the candidate by the authoritative platform event or candidate ancestry; and a non-null `observedSource` must match that same event. A newly fetched target tip must never replace the base used to construct an older candidate. Null repository, event, aggregate, construction, candidate, or base facts are permitted only when acquisition or candidate construction did not complete; they require `mergeSafety: not_established` and an `evidenceResult` of `failed` or `incomplete` as defined below.

Candidate construction does not alter scope or ownership semantics. Core's exit status maps only to `coreResult`. The adapter derives the remaining result fields with these ordered rules:

1. A conclusively observed construction failure, such as a merge conflict, produces `coreResult: not_run`, `evidenceResult: failed`, and a non-null `outcomeReason`; unavailable candidate fields may be null.
2. Missing or contradictory acquisition facts, pre-Core cancellation, stale or invalidated evidence, or unknown enum values produce `evidenceResult: incomplete` and a non-null `outcomeReason`. This incomplete state takes precedence even if a started Core gate also failed; `coreResult` preserves what actually ran.
3. Otherwise, `coreResult: failed` produces `evidenceResult: failed` and a non-null `outcomeReason`.
4. Otherwise, complete and internally consistent evidence with `coreResult: passed` produces `evidenceResult: passed` and `outcomeReason: null`.

`coreResult: not_run` is valid only with `failed` or `incomplete`. Explicitly unavailable freshness or policy may remain a valid diagnostic `passed` result only when `freshnessStatus` and `mergeSafety` are both `not_established`. `head_only` plus `freshnessStatus: established` is impossible and therefore incomplete. Only `target_integrated` construction plus independently `established` freshness, `policyEvidence.bypassPrevention: established`, `coreResult: passed`, and `evidenceResult: passed` may produce `mergeSafety: established`; every other combination produces `not_established`.

## Responsibility Boundaries

| Layer | Responsibility |
| --- | --- |
| Developer branch | Contains one Work Item and its implementation commits. |
| Pull or merge request | Carries review, approval, and platform identity. |
| Git | Builds candidate trees and detects textual merge conflicts. |
| Hosting platform | Provides native queues when available, protects the target branch, and performs the final merge. |
| Platform adapter | Resolves platform events into candidate/base facts and reports unsupported capability without inventing equivalence. |
| Project verification | Detects build, test, lint, and semantic integration failures. |
| AI Cockpit Core | Validates scope, archive ownership, evidence, status consistency, and the complete candidate diff. |
| Human reviewer | Accepts residual risk and controls trusted approval boundaries. |

Core must not read platform APIs merely to discover queue position or maintain cross-request state. Platform-specific event parsing, credentials, and merge execution stay in adapters and installation templates.

## Native Platform Adapters

A target-integrated candidate is not automatically fresh enough to merge. Native adapters must establish both candidate construction and final freshness:

| Platform mode | Construction | Freshness requirement | Permitted conclusion |
| --- | --- | --- | --- |
| GitHub pull-request merge ref only | `target_integrated` at run creation | not established unless an independent rule binds that exact candidate to merge | candidate tested; parallel merge safety not established |
| GitHub Merge Queue `merge_group` | `target_integrated` | required checks reported for the current merge-group SHA, queue-controlled replacement of invalid groups, and policy requiring the governed queue path | parallel merge safety established while the group and policy remain current |
| GitLab detached MR pipeline | `head_only` | not established | head-only branch validation |
| GitLab merged results pipeline only | `target_integrated` at run creation | not established; it does not include other merge requests that may merge concurrently | candidate tested; parallel merge safety not established |
| GitLab Merge Train | `target_integrated` and cumulative | current train pipeline plus evidence that bypass cannot preserve stale train pipelines | established only when the verified train candidate is bound to the final merge; otherwise not established |
| GitLab Free | `head_only`; no supported target-integrated path in this design | not established | head-only diagnostics; parallel merge safety not established |

If platform policy or event evidence cannot prove the listed freshness mechanism, the adapter must downgrade the result instead of inferring safety from a green pipeline.

### GitHub

Normal pull-request validation runs against the pull request candidate available to GitHub Actions. When Merge Queue is enabled, required workflows also listen to `merge_group` with `checks_requested` and run against the merge-group SHA. The adapter profile is available only when the repository can enable Merge Queue and every required workflow reports on that event; otherwise capability detection selects a diagnostic profile.

For the supported Merge Queue path, the authoritative event is the current `merge_group/checks_requested` event. The adapter uses the event's merge-group SHA as `candidateSha` and `aggregateIdentity`, records the repository and workflow-run identity, leaves `observedSource` null unless the event provides one authoritative request/source pair, and resolves the target base from immutable event/API data that belongs to that group. It must verify that the checked-out `HEAD` is the event candidate and that the recorded base is an ancestor of it. Fetching the target ref is allowed only to obtain commit objects; the fetched ref's current tip is not evidence of the candidate's base.

GitHub owns group membership, cumulative ordering, removal, replacement, and final consumption of required-check status. The adapter's terminal action is to publish the result only on the event's merge-group SHA; it does not issue a separate merge command. The queue may merge only the current group whose required checks succeed, so a result on a superseded SHA cannot authorize its replacement. The adapter also verifies that the governed branch requires the queue path and that ordinary actors cannot bypass it. A changed checkout SHA, missing required check, failure to report on that exact SHA, inability to bind the event base, or weaker queue policy invalidates the merge-safe claim. The workflow needs only the permissions required to read the repository/event/policy facts and report its check; if either operation is denied, evidence is incomplete. AI Cockpit audits every changed path and newly introduced archive pair in the complete candidate diff but does not reproduce queue ordering.

### GitLab Premium and Ultimate

Merged results pipelines and Merge Trains provide target-integrated candidate commits. The adapter requires `CI_MERGE_REQUEST_EVENT_TYPE=merge_train` for the supported train path, uses `CI_COMMIT_SHA` as `candidateSha`, uses the internal train candidate and pipeline identity as `aggregateIdentity`, and records the current merge request/source pair as `observedSource`. It reads `CI_MERGE_REQUEST_TARGET_BRANCH_SHA`, `CI_MERGE_REQUEST_SOURCE_BRANCH_SHA`, project identity, merge request identity, pipeline identity, and train event type from the same pipeline. The target SHA becomes `baseSha` only after the adapter verifies that it resolves, is an ancestor of the checked-out candidate, and belongs to that pipeline's event. Predecessor membership remains GitLab-owned and is not inferred from the current request's source SHA. A `merged_result` event remains target-integrated diagnostic evidence, not Merge Train evidence.

When several merge requests are on a train, GitLab owns the cumulative ordering and consumes the status of the pipeline attached to its internal candidate; the adapter does not issue a separate merge command. AI Cockpit sees one candidate tree containing the relevant changes and validates its aggregate evidence. Before reporting success on that pipeline, the adapter must use same-run environment facts and read-only platform settings/train data to verify that candidate and policy still correlate: merged results and Merge Trains are enabled, required pipelines apply, the pipeline still belongs to the recorded train candidate, and no permitted merge path can leave it running after an untested change enters the target. Missing read permission or a non-atomic/unobservable correlation is incomplete and non-authorizing.

GitLab documents both ordinary immediate merge, which restarts affected train pipelines, and an experimental `skip_merge_train` path that can merge without restarting them. It also documents that users with merge permission can bypass a train unless enforcement is enabled. Therefore, Merge Train presence alone never sets freshness to `established`. If skip-without-restart is available, train enforcement is absent or bypassable, policy state cannot be observed reliably, or a bypass event occurs, the adapter invalidates the evidence and reports parallel merge safety as not established. Because GitLab describes train enforcement as not ready for production at the time of this design, an adopter must not infer production-grade enforcement from the feature name.

### GitLab Free

GitLab Free does not provide the Merge Train capability required by this design's supported GitLab path. A normal merge-request pipeline validates the source branch, not the target-integrated result, so it does not correspond to the parallel merge safety guarantee defined here.

AI Cockpit may report head-only diagnostic results for GitLab Free, but it must label parallel merge safety as not established. This document does not define a synthetic compatibility gate, protected merge coordinator, or credential-based replacement for Merge Trains.

## Evidence Strength and User-Facing State

The verification result should expose capability rather than platform jargon. Construction and freshness are separate axes:

| Candidate construction | Freshness status | Bypass prevention | Core result | Evidence result | Permitted conclusion |
| --- | --- | --- | --- | --- | --- |
| `target_integrated` | `established` | `established` | `passed` | `passed` | parallel merge safety established |
| `target_integrated` | `not_established` | any value | `passed` | `passed` | candidate checks passed; parallel merge safety not established |
| `head_only` | `not_established` | any value | `passed` | `passed` | branch checks passed; parallel merge safety not established |
| `target_integrated` or `head_only` | a value consistent with construction | any value | `failed` | `failed` | Core checks failed; parallel merge safety not established |
| `target_integrated` or null | `not_established` | any value | `not_run` | `failed` | candidate construction failed; parallel merge safety not established |
| any value or null | any value or null/impossible | any value | any value | `incomplete` | evidence missing, contradictory, invalidated, or unclassifiable; parallel merge safety not established |

Recommended human-facing output for GitLab Free:

```text
Parallel merge protection: not established
Candidate generation: head-only diagnostic
Reason: GitLab Free does not correspond to the supported Merge Train path
Next action: treat the result as branch diagnostics only
```

`ready_for_review` remains the Cockpit recommendation for Work Item governance readiness. It is independent of candidate merge safety: a Work Item can be ready for human review while `mergeSafety` is `not_established`. Missing or weaker candidate evidence must never produce a merge-safe conclusion.

## Failure Semantics

| Failure | Required behavior |
| --- | --- |
| Target-integrated candidate construction conflict | Set `coreResult: not_run` and `evidenceResult: failed`, report conflicting paths, and do not authorize merge. |
| Candidate/base/source identity mismatch or unreachable commit | Set `incomplete`, record the mismatch, and do not substitute another SHA. |
| Source SHA changes during verification | Invalidate the record and request a new queue/train candidate. |
| Target or cumulative predecessor changes | Let the platform replace/rebuild the candidate; reject results for the superseded event. |
| Project quality check fails | Do not merge; preserve the failing check evidence. |
| AI ownership or archive check fails | Do not merge; report unowned, ambiguous, or out-of-scope paths. |
| No target-integrated candidate can be constructed | Report `head_only` diagnostics and parallel merge safety not established. |
| A target-integrated candidate exists but lacks supported freshness | Preserve `target_integrated`, set freshness and merge safety to `not_established`, and report target-integrated diagnostics. |
| Platform event or policy evidence is missing, delayed, stale, or permission-blocked | Set `incomplete`; preserve available evidence and do not claim parallel merge safety. |
| Queue/train bypass or skip-without-restart occurs | Invalidate affected records immediately and require replacement candidates before any later merge-safe conclusion. |
| Retry is interrupted before Core or its configured limit is reached | Set `coreResult: not_run` when applicable, end as `incomplete`, expose exhaustion, and require explicit requeue rather than reusing evidence. |

The adapter snapshots all identity and policy fields before Core runs, then performs the terminal correlation immediately before reporting the candidate-bound check or pipeline result. GitHub and GitLab consume that result for the same platform candidate; the adapter must not create a second, time-separated authorization. The platform owns candidate replacement; the adapter owns matching terminal evidence to the original event and invalidating its record. An invalidation is monotonic: a record cannot return to valid, and a retry creates a new event identity and evidence record. Rebuilds, cancellation, retry count, retry exhaustion, and the final incomplete state must remain visible in CI output and retained artifacts.

## Security and Trust Boundaries

- Ambient Git repository variables are removed before every public Git operation.
- All fetched SHAs are resolved and recorded explicitly.
- Fork-originated requests do not receive protected automation credentials.
- CI records are execution evidence, not tamper-proof attestations.
- Explicit owner/administrator emergency override, compromised runners, and malicious repository policy changes remain external trust boundaries. Ordinary governed-path bypass must be absent; use of any external override invalidates affected evidence and is never covered by the merge-safe conclusion.

## Installation and Capability Detection

Installation should not silently infer a guarantee from a remote hostname. Doctor or onboarding may detect likely platform facts, but edition, feature availability, branch protection, runner permissions, and credentials must be validated from evidence or left unknown.

The installed project selects one of these profiles:

- GitHub Merge Queue verification.
- GitLab Merge Train verification with separately validated enforcement and no-stale-bypass policy.
- Target-integrated diagnostic verification, including a GitHub pull-request merge ref or GitLab merged results pipeline without final freshness.
- Generic explicit base/head integration.
- Head-only diagnostic mode.

A GitLab project may move from head-only diagnostics to the Merge Train profile after an edition or policy change without changing Work Item schemas.

### Generic Explicit Base/Head Integration

The generic profile is for CI systems that can check out a platform-generated candidate but do not have a bundled adapter. The caller must provide:

- an exact candidate commit checked out as `HEAD`;
- the exact target commit as `AI_BASE_COMMIT`;
- candidate construction (`target_integrated` or `head_only`);
- evidence of how source and target freshness are checked;
- for a requested merge-safe conclusion, the atomic mechanism that prevents a different target state from being merged after verification.

Core validates the candidate diff but does not trust caller labels alone. The generic profile does not establish a supported platform mode by itself. A diagnostic caller records an unavailable atomic mechanism as `freshnessStatus: not_established` and remains non-authorizing. Without a platform-generated target-integrated candidate and a platform freshness mechanism tied to the verified target, the profile is limited to a diagnostic conclusion. Invalid commits, unreachable bases, dirty candidate trees, missing freshness evidence, or an unspecified final update mechanism for a requested merge-safe result fail closed.

## Testing Strategy for a Future Implementation

### Core tests

- The same candidate/base pair produces identical ownership conclusions regardless of platform adapter.
- Multiple valid archive pairs in one candidate pass aggregate PR ownership.
- Unowned, ambiguous, approval-required, and out-of-scope paths fail closed.
- Candidate construction and freshness combinations produce exactly the conclusion matrix above.
- Head-only, target-integrated-but-not-fresh, incomplete, and failed evidence cannot produce `mergeSafety: established`.
- Work Item `ready_for_review` remains independent of candidate `mergeSafety`.
- Invalid or unreachable commits, dirty candidate trees, and candidate/base ancestry mismatches fail closed.
- Schema cases cover null acquisition facts, construction conflict, `coreResult: not_run`, pre-Core interruption, and every valid or invalid result-field combination.

### Adapter tests

- GitHub pull-request and merge-group fixtures resolve candidate, event-bound base, source/group identity, and required checks without substituting the current target tip.
- GitHub fixtures cover a replaced group, source movement, target movement, missing event fields, delayed events, interrupted retries, and required-check failure.
- GitLab detached, merged results, and merge-train fixtures keep construction separate from freshness.
- GitLab fixtures cover train removal/rebuild, source or target movement, missing variables, stale pipeline events, merge conflict, direct bypass, `skip_merge_train` without restart, unavailable enforcement evidence, and retry exhaustion.
- Unknown platform capability or permission-blocked policy detection produces `incomplete`, never an optimistic fallback.
- Platform-specific environment variables do not leak into Contract, Summary, or Archive schemas.

### End-to-end acceptance

- GitHub Merge Queue and GitLab Merge Trains invoke the same Core pre-merge gate.
- Each installed profile produces an explainable construction, freshness, evidence, and merge-safety result.
- Every downgrade and invalidation path prevents a merge-safe conclusion.
- GitLab Free produces an explicit head-only diagnostic result and never a parallel-merge-safe conclusion.

## Rollout Sequence

1. Define and schema-test the platform-neutral evidence record and conclusion matrix. Until it is complete, all adapters default to `mergeSafety: not_established`.
2. Add the GitHub pull-request diagnostic and Merge Queue adapter behind an opt-in flag. Exit only after disposable-repository races prove event/base binding, group replacement, and required-check behavior.
3. Add the GitLab merged-results diagnostic and Merge Train adapter behind a separate opt-in flag. Exit only after disposable repositories prove train rebuild, removal, bypass, `skip_merge_train`, and enforcement detection behavior.
4. Add installer profiles, Doctor capability reporting, and adoption documentation. Unknown or unobservable capability always selects a diagnostic profile, including the explicit GitLab Free non-correspondence state.
5. Run supported adapters in non-authorizing shadow mode and monitor construction mode, freshness downgrades, invalidation causes, rebuilds, retry exhaustion, and false capability detection.
6. Enable merge authorization per platform only after the phase tests and review evidence pass. Rollback disables adapter authorization and returns to diagnostics without changing Work Item schemas or reusing prior candidate evidence.

Each implementation phase requires its own Work Item Contract and verification evidence. Its entry gate is completion of the preceding phase; its exit gate is the named negative/race evidence plus a fail-closed default. The installer must not translate GitLab Free detection into a supported parallel merge safety claim.

## References

- [GitHub: Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [GitHub Actions: `merge_group` event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group)
- [GitHub: `merge_group` webhook payload](https://docs.github.com/en/webhooks/webhook-events-and-payloads#merge_group)
- [GitLab: Merge request pipelines](https://docs.gitlab.com/ci/pipelines/merge_request_pipelines/)
- [GitLab: Merged results pipelines](https://docs.gitlab.com/ci/pipelines/merged_results_pipelines/)
- [GitLab: Merge trains](https://docs.gitlab.com/ci/pipelines/merge_trains/)
- [GitLab: Predefined merge request variables](https://docs.gitlab.com/ci/variables/predefined_variables/)
