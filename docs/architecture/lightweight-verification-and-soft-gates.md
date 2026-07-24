---
author: AI Cockpit maintainers
title: "Lightweight Verification and Soft Gates"
description: "Task, PR, and Release verification stages with shared evidence context."
keywords:
  - verification
  - soft-gates
  - task
  - release
---

# Lightweight Verification and Soft Gates

Verification has three views over one immutable `VerificationContext`:

- **Task** checks changed files and affected tests.
- **PR** checks project health and critical trust boundaries.
- **Release** checks the complete strict proof, including identity, supply chain, installer lifecycle, compatibility, and distribution.

Each checker emits a structured result with a `hard`, `soft`, or `informational` gate. A hard failure remains fail-closed. Complexity growth, archive count, checker count, documentation drift, and duration are trend signals; insufficient history is a warning and may require human confirmation. A check that does not apply to a stage is still emitted as `skipped` with a reason code such as `stage_not_applicable`.

The context reads Git changes, Contract, Summary, Project Profile, impact policy, and complexity policy once per run. Checker registration is deduplicated by ID. Historical archive evidence and repayment records are never rewritten. `current_status.md` remains a generated decision view; structured verification evidence is the machine source.

Use `make ai-verify CONTRACT=... SUMMARY=... STAGE=task|pr|release` for a direct structured run. The existing `make ai-finish`, `make check-ai`, and legacy check targets remain the lifecycle entrypoints.
