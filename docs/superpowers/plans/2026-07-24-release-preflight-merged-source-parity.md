---
author: Ray
title: "Release Preflight Merged-Source Parity"
description: Correct premerge release evidence to use the hosted source identity.
keywords: [ai-cockpit, release, preflight, source-parity]
---
# Release Preflight Merged-Source Parity Plan
> **For agentic workers:** Use a governed Work Item and complete every checkbox before PR.
**Goal:** Make local premerge freeze evidence and hosted release preflight consume one resolved source identity.
**Root cause:** `finalize_release_freeze.py` used Work Item `HEAD` in premerge mode while hosted release checks used merged `SOURCE_COMMIT`.
**Scope/constraints:** Change `scripts/finalize_release_freeze.py`, `tests/test_release_preflight.py`, lifecycle/distribution docs, this plan, and Work Item evidence; do not change v0.5.39 metadata, tag, Release, adopter behavior, archive policy, or archived evidence.
**Test first:** Change the premerge fixture assertion to expect `old-commit`; run `python3 -m pytest -q tests/test_release_preflight.py::test_finalize_release_freeze_premerge_requires_archived_work_item` and observe failure. **Implementation:** In premerge mode resolve `source_commit` with `run_git(["rev-parse", source_identity])`; pass that SHA to both canonical calculations; preserve candidate/default behavior.
**Regression:** The focused test must pass and prove both calculations receive the resolved source SHA.
**Docs:** State that premerge `sourceTree`/`archiveSha256` use controlled `SOURCE_COMMIT`; hosted/local mismatch stops publication until process correction.
**Preflight/verification:** Run `make ai-preflight`, serial-order, budget, before-finish checkpoint, `python3 -m pytest -q tests/test_release_preflight.py`, `make ai-finish`, and `make check-ai-pr AI_BASE_COMMIT=origin/main`; archive growth above 200 is warning-only.
**Lifecycle:** Commit complete archive bundle → push one branch → one PR → all CI green → merge without branch deletion → `make ai-close-work-item TASK=release_preflight_merged_source_parity_v1` → synchronize default branch.
**Release boundary:** Do not retry the v0.5.39 release workflow in this Work Item; only a later user-directed attempt may do so after closure and final audit.
