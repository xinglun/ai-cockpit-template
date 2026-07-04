---
author: Ray
title: "Claude Operating Rules"
description: Claude operating rules for AI Cockpit governed repositories.
keywords:
  - claude
  - ai-cockpit
  - ai-agents
  - governance
---

# Claude Operating Rules

Claude uses the same collaborative AI Cockpit environment as Codex, Gemini, Cursor, Antigravity, and other coding agents. This file is Claude-labeled, but the operating model is not Claude-specific.

## Contract First

Do not begin implementation until the active Work Item Contract describes:

- the task boundary in `scope`;
- files and behavior excluded by `outOfScope`;
- source material used for the decision;
- remaining unknowns;
- acceptance criteria;
- verification commands;
- task-specific rules in `guidelines` (if any).

The Contract is both delegation and description: it assigns the work boundary and makes the task reviewable before implementation begins.

If the Contract contains an `intent` section, read it before implementing. When context is available, fill in at least `intent.problem` (detailed background and gap), `intent.constraints` (constraints to respect), and `intent.rationale` (why this approach). All `intent` fields are optional — do not invent content when context is not provided.

If the Contract has `mode: code`, then `unknowns` must be empty and `notCodable` must be `false`.
If `unknowns` remain or the task is `notCodable`, report that state explicitly instead of forcing implementation.

## Stay Inside Scope

- Do not edit files outside the declared `scope`.
- If the implementation requires another file, update the Contract before changing it.
- Do not remove tests, snapshots, or Work Item records without documenting the reason in the Summary.
- Do not revert user changes unless the user explicitly asks for that revert.

## Summary Required

Before declaring the work complete, update the matching Summary with:

- changed files and reasons;
- sources used;
- verification commands and results;
- compliance details for each of the task's guidelines in `guidelinesCompliance`;
- remaining unknowns;
- risk level and detail;
- generated files;
- destructive changes;
- observed issues.

Summary is both an audit record and a collaboration handoff for the next reviewer or agent. Use checkpoints to prevent drift during longer tasks.
Run `make ai-finish TASK=<task>` when the Summary is ready.
