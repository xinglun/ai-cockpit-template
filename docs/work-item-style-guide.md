---
author: Ray
title: "Work Item Style Guide"
description: Practical guidance for writing reusable Work Items in AI Cockpit.
---

# Work Item Style Guide

## Objective First

Start with the outcome. State what should be true when the work is done before describing implementation details.

## Explain the Problem

Say why the work exists. If no product context was provided, say that plainly instead of inventing motivation, impact, or user pain.

Use `problemStatement` for a one-line summary of the problem. Use the `intent` section to provide richer context when it is available:

- `intent.problem` — detailed background, current state, and the gap this work closes.
- `intent.constraints` — implementation or design constraints the agent must respect.
- `intent.rationale` — why this approach was chosen over alternatives.

`businessGoal`, `userGoal`, and `nonGoals` are available for future workflows; leave them empty when context is not provided. Do not invent intent fields when motivation has not been stated — prefer explicit `not provided` over inferred explanations.

The `intent` section can be omitted entirely without breaking validation. All fields are optional.


## Scope Before Implementation

Declare allowed and out-of-scope files before changing code. Scope is a boundary, not a summary after the fact.

## Explicit Non-Goals

List what must not change. This keeps review focused and prevents accidental expansion.

## Machine-Verifiable Acceptance

Acceptance criteria should be observable or checkable.

Bad:

- Looks good.

Good:

- Contract validation passes.
- Empty `problemStatement` fails when present.

## Minimal Process

Do not add new workflow steps, approval ceremonies, or schema fields unless they preserve review or audit value.

## Executable Verification

Reference executable checks, usually Make targets or registered check IDs.

## Prefer Extending Existing Concepts

Before adding a new field or concept, check whether an existing field can carry the evidence clearly.

## Documentation Before Schema

Document the review model first. Add schema only when the repository needs additional machine-verifiable evidence.
