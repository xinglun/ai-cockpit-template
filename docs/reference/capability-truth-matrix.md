---
author: Ray
title: "Capability Truth Matrix"
description: Evidence-backed distinction between implemented, template-only, adopter-installed, and planned AI Cockpit capabilities.
keywords:
  - ai-cockpit
  - capability-truth
  - evidence-governance
  - conditional-go
---
# Capability Truth Matrix

This matrix is the source of truth for public capability language during the Conditional GO remediation. The machine-readable record is [capability-truth-matrix.json](capability-truth-matrix.json); each row must use one of four statuses:

- `implemented`: verified in the repository by a command, source, and regression evidence.
- `template_only`: present in template code or documentation, but not proof of an adopter's installed capability.
- `adopter_installed`: produced and verified in an adopter repository; the evidence must name the installed runtime or fixture.
- `planned`: a remediation target without current evidence sufficient for an implemented claim.

## Current boundary

AI Cockpit is a Repository Governance Layer. It is not an Agent Runtime, Workflow Engine, Security Sandbox, identity system, or enterprise compliance control. The matrix therefore separates repository-local governance evidence from adopter-installed behavior and external release/security evidence.

## Reading rules

Documentation may claim a capability as current only when the corresponding matrix row is `implemented` or `adopter_installed` and its evidence paths are independently verifiable. `template_only` describes available template material, not a completed target-repository result. `planned` rows must remain visibly future work until their dedicated Work Item supplies commands, tests, and evidence.

The matrix deliberately records the current gap around ten-stage calibration, Candidate activation, Bootstrap lifecycle, Ownership Manifest, verified Quick Install archive digests, and independent CI/Release Evidence. Those capabilities are addressed by later serial Work Items in the [Conditional GO remediation plan](../superpowers/plans/2026-07-22-conditional-go-review-remediation.md).

For exact row-level evidence, status vocabulary, and missing-evidence reasons, use the JSON source rather than inferring status from prose.
