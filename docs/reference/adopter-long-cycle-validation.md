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

This is controlled fixture evidence. It does not prove enterprise identity, authorization, immutable audit, regulatory compliance, provider workflow behavior, or production readiness.
