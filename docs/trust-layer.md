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

## What is evidence?

Evidence is a reviewable record produced by a repository or an independent verification tool: a Contract, a diff, a test result, a coverage report, a baseline comparison, a signed platform review, or an archived Summary. An agent explanation can help a reviewer understand a result, but it is not evidence by itself. A screenshot, a chat assertion, or a self-declared approval is likewise not an independent authorization.

The flow is:

```text
Intent → Contract → Preflight → Change → Verification → Summary → Human decision
```

When a signal is missing, stale, contradictory, outside scope, or high risk, the governed path stops. A human can resolve the uncertainty by recording a decision and new evidence; the next step re-runs the relevant checks rather than trusting the conversation alone.

The template uses the enforced Preflight profile by default. `.ai/guards/preflight_review_policy.yaml` sets `profile: enforced`, enables the gate, and blocks `needs_human_confirmation`, `human_decision_recorded`, and `not_ready`. Only a newly computed `ready` report can proceed through the governed start or finish path. An adopter may choose an explicit compatibility profile with `profile: advisory`, `gateEnabled: false`, and an empty `blockedStatuses` list, but advisory mode is not evidence that the Trust Layer can stop an agent at the protocol level.

## Raw request and capability binding

For a full Contract v2 `MODE=code` Work Item, `rawUserRequest` is required evidence whenever the scope includes the active Work Item Contract. Omitting it is fail-closed; it cannot silently become `Not Applicable`. A registered exemption is allowed only for `system_maintenance`, `dependency_upgrade`, `release_metadata`, or `internal_governance` tasks, and the exemption must be explicit in `rawRequestExemption`.

When `rawUserRequest` is present, the Contract must also include portable `rawRequestSource` evidence: `type` (`human`, `issue`, `pr_comment`, or `system`), `reference`, `capturedAt`, and `digest`. Active Contract v2 code Work Items must additionally provide structured `requestedOperation` fields: `target`, `action`, `environment`, `effect`, and boolean `authorityRequired`. The Intent Capability signal derives required capabilities from the repository-owned `operationMappings` policy; the separate Implementation Capability signal derives capabilities from the actual scope paths. A self-declared `requestedCapabilities` list cannot authorize an unmapped operation or replace either evidence source. An explicitly unsupported operation, such as making a rocket, remains blocked even if the changed paths are only documentation or tests. The initial vocabulary is intentionally narrow; broader multilingual and hidden-risk interpretation is tracked separately and is not implied by this boundary check.

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
