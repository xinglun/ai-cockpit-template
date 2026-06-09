---
author: Ray
title: "AI Cockpit"
description: AI Cockpit workspace overview and workflow guide.
keywords:
  - ai-cockpit
  - work-item-contract
  - scope-guard
  - change-summary
  - cockpit-status
---

# AI Cockpit

AI Cockpit is a small governance layer for agentic coding. It gives Codex, Gemini, Antigravity, or another coding agent a shared operating contract before files are changed.

The cockpit is intentionally language-agnostic. The Python scripts validate the AI workflow, while the Makefile delegates product-specific checks to commands that each repository can customize.

## Core Files

- `checks.yaml`: check catalog and project-specific command selection guidance.
- `current_status.md`: generated status view for the active Work Item.
- `.ai/work-items/active/*.contract.json`: task boundary before work starts.
- `.ai/work-items/active/*.summary.json`: change report before finish.
- `.ai/guards/*.yaml`: file ownership, boundary, scope, backtrack, and coverage rules.

## Flow

1. Create a Work Item with `make ai-start TASK=<task> TITLE="..." MODE=code`.
2. Edit the Contract until scope, sources, acceptance, verification, risk assessment, agent capability, and execution decision are explicit.
3. Implement only inside the declared scope.
4. Update the Summary with changed files, checks, risks, review readiness, boundary checks, known gaps, and any destructive changes.
5. Run `make ai-finish TASK=<task>`.
6. Review the generated status and archived Contract/Summary.

`current_status.md` is generated. Do not hand-edit it.

## Lifecycle Checks

`make ai-start` runs a lifecycle preflight before creating a new skeleton. It refuses to start when active Contract/Summary files are unpaired, more than one Work Item is active, or `current_status.md` disagrees with the active/no-active state.

Run `make check-ai-status-consistency` after generating or checking `current_status.md` when you need to validate the lifecycle state without finishing the Work Item.

## Review Readiness

The Contract readiness fields record whether the agent can implement and verify the task before coding starts. The Summary readiness fields record residual risks, expected review focus, boundary checks, user corrections, known gaps, and claims that were not verified.

Keep these fields language-neutral when this template is copied into another repository.
