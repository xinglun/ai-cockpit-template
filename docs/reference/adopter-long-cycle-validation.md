---
author: Ray
title: External Adopter Long-Cycle Validation
description: Controlled independent-repository evidence for install, upgrade, rollback, PR, and cleanup lifecycle boundaries.
keywords:
  - adopter
  - lifecycle
  - validation
---

# External Adopter Long-Cycle Validation

Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/external_adopter_long_cycle.py` to execute the deterministic harness. It creates an isolated temporary Git repository and bare `origin`, records the default branch and baseline commit, performs an upgrade in a separate worktree, merges it, rolls it back, and verifies local and remote branch cleanup.

This is controlled fixture evidence. It does not prove enterprise identity, authorization, immutable audit, regulatory compliance, provider workflow behavior, or production readiness. Run `make cross-stack-long-cycle` to aggregate Python and Java dependency-free fixture phases with the isolated adopter Git lifecycle. The TypeScript fixture has an additional real npm lifecycle test: its `lifecycle.mjs` executes install, build, test, lint, format, and local upgrade/rollback transitions, and records `executionKind` as `local_real_execution`, `blocked`, or `not_run`. The generic `fixture_harness.py` remains deterministic manifest simulation and must not be cited as real TypeScript execution. Install, Configure, Normal Work Item, Ambiguous Request, Critical Domain Change, Upgrade, Rollback, and Release Check remain explicit phases; blocked phases include resume conditions. Provider and identity evidence remain `not_run`, and enterprise assurance remains `not_claimed`.
