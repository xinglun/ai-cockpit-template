---
author: Ray
title: "V2 Implementation Plan"
description: Incremental implementation phases for V2 Intent-aware Development milestone.
keywords:
  - ai-cockpit
  - v2
  - intent
  - implementation-plan
  - roadmap
---

# V2 Implementation Plan

This document defines the incremental implementation phases for AI Cockpit V2: Intent-aware Development.

## Overview

V2 introduces Intent as a first-class governance object. The implementation is divided into four incremental phases, each deliverable as an independent pull request.

## Phase 1: Roadmap Documentation

**Status**: Current phase

**Scope**:
- Revise `docs/roadmap.md` to establish new architectural positioning
- Update `README.md` and localized versions to emphasize Repository Governance Layer positioning
- Update `.ai/README.md` and `.ai/cockpit/README.md` to align with governance-first terminology
- Update `.ai/glossary.md` with Intent-related terminology
- Create this implementation plan document

**Goal**: Establish clear architectural foundation before any implementation work.

**Key Deliverables**:
- Four design principles clearly documented: Model Agnostic, Stable Schema, Governance Over Workflow, Intent-driven Development
- Governance loop visualization: Intent → Contract → Implementation → Verification → Summary
- V2 positioning as "Intent as first-class governance object"
- Clear distinction: AI Cockpit is Repository Governance Layer, not Agent Runtime or Workflow Engine

**Acceptance**:
- Documentation accurately reflects Intent → Contract → Implementation → Verification → Summary governance loop
- Design principles are stated clearly and consistently across all documentation
- No breaking changes to existing schemas or workflows
- All intent fields documented as optional

**Dependencies**: None

---

## Phase 2: Contract Schema Validation

**Status**: Not started

**Scope**:
- Verify V2 Contract schema already supports all intent fields correctly
- Audit all Contract validation logic to ensure optional intent fields are handled properly
- Update Contract field documentation to reflect intent field semantics
- Ensure `contractVersion: 2` handling is complete and backward-compatible with V1

**Goal**: Confirm schema stability and validation correctness.

**Key Deliverables**:
- Contract schema validation supports all optional intent fields
- Validator handles missing/null intent fields gracefully
- Documentation aligns with implemented schema
- Test coverage for intent field validation

**Acceptance**:
- All validators pass with intent fields present, missing, or null
- No breaking changes to existing Contract validation
- Contract version 2 is fully backward-compatible with version 1 (legacy read-only)

**Dependencies**: Phase 1 (documentation foundation)

---

## Phase 3: Summary Intent Alignment

**Status**: Not started

**Scope**:
- Design Summary `intentAlignment` section schema
- Implement Summary validation for optional intentAlignment fields
- Update Summary template to include intentAlignment section
- Document intentAlignment semantics and usage

**Goal**: Enable Summaries to validate alignment back to declared Intent.

**Key Deliverables**:
- Summary schema includes optional `intentAlignment` section
- Fields: `problemResolved`, `constraintsRespected`, `nonGoalsAvoided`, `rationaleValidated`
- Validators handle intentAlignment gracefully
- Documentation explains how to use intentAlignment

**Acceptance**:
- Summary validation accepts intentAlignment fields
- Summary template includes intentAlignment section with clear guidance
- Validators do not require intentAlignment when intent is not present in Contract
- Documentation shows concrete examples of intentAlignment usage

**Dependencies**: Phase 2 (schema validation)

---

## Phase 4: Templates & AI Integration

**Status**: Not started

**Scope**:
- Update Work Item Contract template with improved intent field guidance
- Update agent operating rules (AGENTS.md) to reference intent as first-class governance object
- Add checkpoint reporting for intent context
- Update examples to demonstrate intent usage patterns
- Add steering guidance for agents to leverage intent fields naturally

**Goal**: Make intent fields easily discoverable and naturally usable by AI agents.

**Key Deliverables**:
- Contract template shows clear intent field examples
- Agent rules guide agents to read and respect intent context
- Checkpoint output includes intent summary
- Examples demonstrate intent usage for common scenarios
- Steering files guide agents to fill intent fields when context is available

**Acceptance**:
- Contract template includes helpful intent field guidance
- Agents can discover intent fields through templates and rules
- Checkpoint output surfaces intent context clearly
- Examples cover at least 3 common intent usage patterns
- Documentation clarifies "all fields optional" principle

**Dependencies**: Phase 3 (Summary intentAlignment)

---

## Validation Strategy

Each phase is validated independently:

1. **Phase 1 (Documentation)**: Manual review for clarity, consistency, and accuracy
2. **Phase 2 (Schema)**: Automated validator tests with intent fields present/missing/null
3. **Phase 3 (Summary)**: Automated validator tests for intentAlignment section
4. **Phase 4 (Integration)**: End-to-end workflow tests with intent-aware Contracts

All phases must preserve backward compatibility. Existing V1 Contracts and workflows continue to function without modification.

---

## Success Criteria

V2 implementation is complete when:

1. All four phases are merged
2. Documentation clearly positions Intent as first-class governance object
3. Contract and Summary schemas support intent and intentAlignment
4. Validators handle all optional fields correctly
5. Templates and agent guidance make intent discoverable
6. No breaking changes to existing workflows
7. Governance loop (Intent → Contract → Implementation → Verification → Summary) is clearly documented and implemented

---

## Non-Goals

V2 explicitly does **not** include:

- Making intent fields mandatory
- Breaking changes to V1 Contract format
- Automated intent validation or constraint checking (deferred to V3 consideration)
- Repository-level knowledge management (V3 scope)
- Organization-level governance (V4 scope)

---

## Related Documentation

- [Roadmap (V1–V4)](../roadmap.md)
- [Contract Fields Manual](../contract-fields.md)
- [Design Philosophy](../philosophy/design-philosophy.md)
- [Agent Operating Rules](../../AGENTS.md)
