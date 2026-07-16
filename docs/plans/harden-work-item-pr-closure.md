---
author: Codex
title: "Harden Work Item PR Closure Plan"
description: Implementation and verification plan for Work Item PR closure workflow hardening.
keywords:
  - ai-cockpit
  - work-item
  - branch
  - verification
---

# Plan: Harden Work Item PR Closure

1. Add failing regression tests for `ai-finish` on the discovered base branch and for the actionable `ai-close-work-item` diagnostic.
2. Implement a provider-neutral base-branch guard in `ai_finish.py` without changing feature-branch finish behavior.
3. Improve the closure error text and update `AGENTS.md`, Cockpit README, repository workflow reference, and first-Work-Item guide with the canonical order and prohibited shortcuts.
4. Run focused tests, then all required AI and project checks; update the Contract/Summary and generated status.
5. Commit, push, create the PR, and after merge perform lifecycle closure from the Work Item branch before confirming clean synchronized `main`.
