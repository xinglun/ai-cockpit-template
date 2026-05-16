---
author: Ray
title: "Case Study: Stopping AI Rollback Corruption"
description: Case study showing how AI Cockpit prevents AI rollback corruption.
keywords:
  - ai-cockpit
  - case-study
  - ai-rollback-corruption
  - code-review
  - ai-change-governance
---

# Case Study: Stopping AI Rollback Corruption

## The Failure

An AI coding agent was asked to update session validation.

The intended scope was small:

```text
src/auth/session.rs
tests/auth/session_test.rs
```

But the generated diff touched unrelated payment code:

```text
src/auth/session.rs
tests/auth/session_test.rs
src/auth/payment.rs
src/billing/retry_policy.rs
```

The reviewer saw a plausible patch, but the real risk was hidden:

- unrelated files changed;
- a previous payment guard was partially rolled back;
- tests did not explain the behavior change;
- no summary explained why billing code was touched.

This is rollback corruption: the AI does not just make a new mistake. It silently erodes completed work.

## The AI Cockpit Version

The Work Item Contract declares the boundary before edits:

```json
{
  "workItemId": "session-validation",
  "scope": [
    "src/auth/session.rs",
    "tests/auth/session_test.rs"
  ],
  "outOfScope": [
    "src/auth/payment.rs",
    "src/billing/**"
  ]
}
```

The agent edits files.

Scope Guard checks the actual git diff:

```text
[BLOCKED]
Scope violation detected.

Unauthorized file modification:
- src/auth/payment.rs
- src/billing/retry_policy.rs

Allowed scope:
- src/auth/session.rs
- tests/auth/session_test.rs
```

The merge stops before review starts.

## The Difference

Before:

```text
AI changed 24 files.
Nobody knows why.
Review starts from confusion.
```

After:

```text
Task scope declared.
Unauthorized changes blocked.
Summary required.
Cockpit status generated.
Review starts from context.
```

## Why It Matters

AI coding gets dangerous when changes become unbounded and unaudited.

AI Cockpit does not try to make the agent smarter. It makes the change process controlled:

```text
Contract -> Guard -> Summary -> Status -> Archive
```

