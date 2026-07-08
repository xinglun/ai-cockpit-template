---
author: Ray
title: "V2.5 Governance Compression Plan"
description: Development plan for AI Cockpit V2.5 Governance Compression, converting repository truth into human decision state.
keywords:
  - ai-cockpit
  - v2.5
  - governance-compression
  - cockpit-status
  - human-review
---

# V2.5 Governance Compression Plan

This document defined the development plan for AI Cockpit V2.5: Governance Compression.
The plan has now been executed and is retained as a reference for the implemented architecture.

## Overview

V2.5 shifts Cockpit from a feature primarily discussed from the AI completion perspective to a human review decision layer.

The core objective is:

```text
Convert repository truth into human decision.
```

As AI-assisted implementation becomes more capable, repository governance produces more information: Intent, Contract, verification evidence, acceptance evidence, residual risks, guideline compliance, checkpoint evidence, and future repository context. This information is valuable, but reviewers should not need to inspect all of it directly before answering operational questions such as:

- Can this be merged?
- Is this ready for review?
- Should this be blocked?
- Does this need investigation?

V2.5 positions Cockpit as the compression layer that consumes repository truth and presents a concise, explainable operational state for human decision-making.

## Architectural Positioning

V2 establishes the governance loop:

```text
Intent
  ↓
Contract
  ↓
Implementation
  ↓
Verification
  ↓
Summary
```

V2.5 extends the loop:

```text
Intent
  ↓
Contract
  ↓
Implementation
  ↓
Verification
  ↓
Summary
  ↓
Cockpit
  ↓
Human Decision
```

The layers answer different questions:

| Layer | Primary Question |
| --- | --- |
| Intent | Why do this? |
| Contract | How should this be done? |
| Summary | What actually happened? |
| Cockpit | What decision should a human make now? |

## Repository Truth vs Human Decision

Summary is the repository truth layer. It should prioritize completeness and auditability.

Examples of Summary facts:

- Changed files
- Verification evidence
- Intent Alignment
- Acceptance evidence
- Unknown resolution
- Guideline compliance
- Residual risks
- Checkpoint evidence

Cockpit is the human decision layer. It should prioritize clarity, operational usefulness, and traceability back to Summary evidence.

Examples of Cockpit governance state:

- Intent: Resolved
- Acceptance: Complete
- Unknowns: Resolved
- Verification: Passed
- Companion coverage: Complete
- Residual risk: Low
- Recommendation: Ready for Review

Cockpit does not replace Summary. It derives its state from Summary.

```text
Repository Truth
  ↓
Governance Compression
  ↓
Operational Status
```

## Completion Assurance

Completion Assurance becomes one component of Governance Compression.

Examples:

| Raw Governance Area | Compressed Signal |
| --- | --- |
| Acceptance evidence | Complete |
| Unknowns | Resolved |
| Intent Alignment | Aligned |
| Companion rules | Satisfied |
| Verification evidence | Passed |

These are governance signals rather than raw repository data. The V2.5 milestone should avoid making Completion Assurance the entire product theme.

## Design Principles

### Repository Truth First

Summary remains the source of repository truth. Cockpit must not invent information that is not present in Summary, Contract, or generated check evidence.

### Compression

Cockpit exposes only the information needed for human decision-making. Detailed evidence remains available in Summary and linked governance records.

### Generic

Cockpit remains repository-agnostic. Project-specific rules continue to come from repository policies, check catalogs, guards, and Work Item configuration.

### Explainable

Every Cockpit status should be traceable back to Summary evidence. V2.5 should avoid hidden reasoning and opaque status derivation.

### Human Review First

V2.5 optimizes for reviewers, maintainers, and approvers. It should help humans decide merge, review, block, or investigate without manually reconstructing the full governance state.

## Implementation Phases

V2.5 should be delivered incrementally after the V2 Intent-aware Development foundation is stable.

### Phase 1: Documentation and Information Architecture

**Status**: Completed

**Scope**:

- Update roadmap positioning to introduce V2.5 between V2 and V3.
- Document Summary as repository truth and Cockpit as human decision state.
- Define canonical Governance Compression terminology.
- Clarify that Completion Assurance is a component, not the milestone name.

**Acceptance**:

- Documentation consistently uses "Governance Compression" for V2.5.
- Summary and Cockpit responsibilities are separated clearly.
- V2 remains positioned as Intent-aware Development and is not replaced by V2.5.

### Phase 2: Cockpit Status Model Design

**Status**: Completed

**Scope**:

- Define the compressed status fields Cockpit should present.
- Map each field to required Summary, Contract, or check evidence.
- Define recommendation states such as `ready_for_review`, `ready_with_risks`, `needs_investigation`, and `blocked`.
- Define how residual risks affect the recommendation.

**Acceptance**:

- Every Cockpit field has an evidence source.
- Recommendation states are generic and repository-agnostic.
- The model distinguishes raw facts from derived operational status.

### Phase 3: Summary Evidence Normalization

**Status**: Completed

**Scope**:

- Audit Summary fields used for Cockpit derivation.
- Normalize evidence needed for intent, acceptance, unknowns, verification, guideline compliance, residual risks, checkpoint evidence, and companion coverage.
- Keep fields optional where possible to preserve backward compatibility.
- Identify any gaps where Cockpit cannot derive status without new Summary evidence.

**Acceptance**:

- Cockpit derivation inputs are explicit.
- Missing evidence produces conservative status, not invented confidence.
- Existing Summary records remain valid.

### Phase 4: Status Generation

**Status**: Completed

**Scope**:

- Update generated Cockpit Status to present compressed governance state.
- Keep links or references to the Summary evidence behind each status.
- Preserve lifecycle consistency checks.
- Avoid hand-edited generated status files.

**Acceptance**:

- Generated status answers the human review question directly.
- Status output remains concise and explainable.
- Existing Work Item lifecycle checks still pass.

### Phase 5: Policy and Review Integration

**Status**: Completed

**Scope**:

- Connect governance compression to review policy and risk policy outputs.
- Ensure governance-sensitive paths influence review focus and recommendation.
- Document reviewer interpretation of recommendation states.
- Add examples for common review outcomes.

**Acceptance**:

- Reviewers can interpret Cockpit status without reading every Summary field first.
- Risk and review policy results are reflected as compressed signals.
- Project-specific policies remain external to the generic Cockpit model.

### Phase 6: Tests, Compatibility, and Migration

**Status**: Completed

**Scope**:

- Add tests for status derivation from complete, partial, risky, and blocked Summary records.
- Validate backward compatibility with archived Work Items.
- Ensure missing V2.5 fields degrade conservatively.
- Update examples and templates only after the model is stable.

**Acceptance**:

- Existing V1/V2 governance records remain readable.
- New status derivation is covered by focused tests.
- Migration requirements are documented before release.

## Release Hardening Notes

V2.5 is implemented, but the release-hardening pass should still validate the status model against real Work Items before V3 is introduced.

Focus areas:

- Validate Cockpit recommendation behavior on clean, risky, incomplete, and unresolved Work Items.
- Keep reviewer-facing examples aligned with the generated status renderer.
- Confirm that `needs_investigation` is not overused for cases that are already clearly blocked or ready.
- Ensure `ready_with_risks` remains useful when the work is complete but residual risk deserves attention.
- Keep the review model explainable without adding new schema fields or longer output.

The reviewer-oriented reference for this pass is [How to Read Cockpit Status](how-to-read-cockpit-status.md).

## Validation Strategy

V2.5 validation should prove that Cockpit compresses truth without inventing it:

1. Documentation review confirms the architecture separates Summary and Cockpit responsibilities.
2. Status model tests verify every compressed signal maps to explicit evidence.
3. Negative tests verify missing evidence results in `needs_investigation`, `not_ready`, or another conservative state.
4. Lifecycle tests verify generated status remains consistent with active Work Item records.
5. Review policy tests verify governance-sensitive changes remain visible to human reviewers.

## Success Criteria

V2.5 is complete when:

1. Governance Compression is documented as the V2.5 theme.
2. Summary is treated as repository truth.
3. Cockpit is treated as human decision state.
4. Completion Assurance is implemented as one compressed governance signal.
5. Generated Cockpit Status provides concise recommendation-oriented output.
6. Every Cockpit signal is traceable to Summary, Contract, or check evidence.
7. Missing or incomplete evidence leads to conservative status.
8. Existing V1/V2 workflows remain compatible.

## Non-Goals

V2.5 does not include:

- Replacing V2 Intent-aware Development.
- Moving repository truth out of Summary.
- Making Cockpit a second audit record.
- Requiring humans to trust hidden reasoning.
- Introducing repository-specific governance rules into generic scripts.
- Implementing V3 repository intelligence or V4 organization governance.

## Related Documentation

- [Roadmap (V1-V4)](../roadmap.md)
- [V2 Implementation Plan](v2-implementation-plan.md)
- [Contract Fields Manual](../contract-fields.md)
- [Design Philosophy](../philosophy/design-philosophy.md)
