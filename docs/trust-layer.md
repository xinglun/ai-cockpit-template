---
author: Ray
title: "Trust Layer"
description: Evidence, decisions, and fail-closed behavior in AI Cockpit.
keywords:
  - ai-cockpit
  - trust-layer
  - evidence
  - human-decision
---

# Trust Layer

AI Cockpit's Trust Layer answers one operational question: **does the available evidence support continuing, or must the agent stop?** It governs repository changes; it does not grant an agent authority to deploy, approve itself, or replace security and quality tools.

The formal regression entrypoint is the **Unsupported Claim Regression Gate** (`make unsupported-claim-regression`), complemented by the mandatory known-scenario gate (`make delusion-test-gate`). Together they block claims with missing evidence, `not_run` or failed checks described as passed, inference presented as fact, nonexistent files, unsupported approval claims, simulation presented as real execution, and the explicitly enumerated rocket, transaction-success, checker-bypass, test-deletion, and underspecified-work fixtures. A claim backed by an existing structured evidence file may pass. The gate is part of the repository quality target used by Work Item Finish and CI/release quality paths, so a negative regression cannot be merged as green. These gates evaluate external repository claims and a finite deterministic fixture vocabulary; they do not detect an LLM's internal state or provide universal semantic coverage. “Delusion” remains a compatibility label for this known-scenario regression target.

## What is evidence?

Evidence is a reviewable record produced by a repository or an independent verification tool: a Contract, a diff, a test result, a coverage report, a baseline comparison, a signed platform review, or an archived Summary. An agent explanation can help a reviewer understand a result, but it is not evidence by itself. A screenshot, a chat assertion, or a self-declared approval is likewise not an independent authorization.

The flow is:

```text
Intent → Contract → Preflight → Change → Verification → Summary → Human decision
```

When a signal is missing, stale, contradictory, outside scope, or high risk, the governed path stops. A human can resolve the uncertainty by recording a decision and new evidence; the next step re-runs the relevant checks rather than trusting the conversation alone.

All Trust Layer Guard signals use a shared additive envelope: `signalId`, `state`, `confidence`, `evidence`, `policyReference`, `humanDecisionAllowed`, and `safeAlternatives`, alongside the legacy `name`, `value`, and `sources` fields. This metadata standardizes explanation and lifecycle-gate handling; confidence is deterministic evidence quality, never authorization, and a human decision cannot turn a blocked signal into an unverified pass.

The template uses the enforced Preflight profile by default. `.ai/guards/preflight_review_policy.yaml` sets `profile: enforced`, enables the gate, and blocks `needs_human_confirmation`, `human_decision_recorded`, and `not_ready`. Only a newly computed `ready` report can proceed through the governed start or finish path. An adopter may choose an explicit compatibility profile with `profile: advisory`, `gateEnabled: false`, and an empty `blockedStatuses` list, but advisory mode is not evidence that the Trust Layer can stop an agent at the protocol level.

## Raw request and capability binding

For a full Contract v2 `MODE=code` Work Item, `rawUserRequest` is required evidence whenever the scope includes the active Work Item Contract. Omitting it is fail-closed; it cannot silently become `Not Applicable`. A registered exemption is allowed only for `system_maintenance`, `dependency_upgrade`, `release_metadata`, or `internal_governance` tasks, and must be a structured `rawRequestExemption` record containing `policyRef`, `triggerRef`, applicability, and `approvedBy`. Free text, unknown values, missing sources, and high-risk exemptions fail closed; the canonical policy is `.ai/policies/raw-request-exemptions.yaml`.

When `rawUserRequest` is present, the Contract must also include portable `rawRequestSource` evidence: `type` (`human`, `issue`, `pr_comment`, or `system`), `reference`, `capturedAt`, and `digest`. Active Contract v2 code Work Items must additionally provide structured `requestedOperation` fields: `target`, `action`, `environment`, `effect`, and boolean `authorityRequired`. Policy Evaluation reads the canonical allowlist from `.ai/policies/requested-operation.yaml`; the Intent Capability signal derives required capabilities from repository-owned `operationMappings`, while Diff Ownership classifies actual changed paths. A self-declared `requestedCapabilities` list cannot authorize an unmapped operation or replace either evidence source. Policy-disallowed combinations and missing `authorityEvidence` when authority is required fail closed before implementation. An explicitly unsupported operation, such as making a rocket, remains blocked even if the changed paths are only documentation or tests. Raw request exemptions additionally require a registered trigger (`scheduled-maintenance`, `automated-dependency-update`, `release-automation`, or `internal-governance`), applicability limited to `repository`, `sandbox`, or `test`, no unknown fields, and a non-high-risk contract; the canonical rules are in `.ai/policies/raw-request-exemptions.yaml`. The initial vocabulary is intentionally narrow; broader multilingual and hidden-risk interpretation is tracked separately and is not implied by this boundary check.

The Intent Guard also handles a small, explicit evidence boundary for underspecified requests. Generic improvement phrases, including the supported Chinese examples `随便改改` and `大概改一下`, produce a `Partial` signal when the Contract intent does not declare a concrete `target`, `expectedOutcome`, and `successEvidence`. The signal lists the missing categories so the request can be narrowed and re-run. Existing keyword ambiguity detection remains in force; this check does not claim broad semantic or multilingual classification.

Guard signals use one Decision Model: canonical states are `allow`, `review`, `confirm`, `block`, `error`, and `not_applicable` (with internal `defer` retained only where execution status requires it). Legacy values such as `Ready`, `Partial`, and `Inconsistent` are compatibility labels derived one-way from canonical state; consumers must not author contradictory value/state pairs.

Success Criteria are Work Item-owned when an active Contract has a sibling `.ai/work-items/active/<task>.success.json`. Preflight validates and consumes that declaration first, so concurrent Work Items can isolate their criteria. The legacy `.ai/project/success_criteria.json` remains an explicit compatibility fallback for historic or unassigned Work Items. Archiving moves the task-owned declaration with the Contract and Summary, preserving lifecycle evidence without making the global file the only source.

## Human decisions and recovery

A decision request should state the blocked condition, evidence, risk, available options, recommendation, and the condition for resuming. The human decision is a workflow record, not proof that the underlying check passed. After recovery, run Preflight and the project checks again, then archive the resulting Summary.

Typical safe options are:

1. provide the missing repository or platform evidence;
2. narrow the scope to a verifiable local alternative; or
3. stop and preserve the evidence for review.

## Non-goals and boundaries

The Trust Layer does not make an LLM's confidence authoritative, replace branch protection or CODEOWNERS, create trusted identity, run production operations, or replace tests, scanners, SBOM/provenance tooling, or release-provider evidence. Those systems remain responsible for the facts they produce; AI Cockpit records and governs how those facts support a repository decision.

For structured critical-domain requests, the guard evaluates `target`, `action`, `environment`, and `effect` together. Documentation, read-only work, tests, and sandbox mocks can remain ready; explicit effects such as force-success, validation bypass, authorization bypass, or production execution are blocked with a signal ID, policy reference, evidence, safe alternative, and resume condition. This is deterministic boundary coverage, not complete semantic risk classification.

Run the local failure-oriented demonstration:

```sh
./docs/examples/trust-layer-demo.sh
```

It is intentionally offline and harmless. Every unsafe scenario is blocked, and the final JSON report records `unsafeOperations: 0`.
Archived Work Item evidence has an immutable root: `*.archive-manifest.json` is generated after the Contract and Summary are frozen and records their SHA-256 digests in a fixed, non-self-referential structure. The archive index may discover legacy Contract/Summary pairs without this manifest, but new archive entries reference the manifest digest. Generated `current_status.md` remains operational status and is excluded from this immutable chain.
