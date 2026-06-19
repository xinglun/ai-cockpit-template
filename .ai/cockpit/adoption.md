---
author: Ray
title: "Adoption Readiness"
description: Installed, repository-local guidance for completing AI Cockpit adoption.
---

# Adoption Readiness

Installation deploys the governance runtime. It does not prove that project-specific quality commands, Coverage Guard paths, or pull-request CI are correct.

Before making AI Cockpit a required production gate:

1. Run `make cockpit-doctor` to record project facts, evidence, confidence, candidate boundaries, Guard mismatches, and unknowns.
2. Run `make cockpit-calibrate`. Review the proposed Profile without treating suggestions as approvals.
3. Create `.ai/project_profile.yaml` with explicitly confirmed boundaries and approval metadata. Resolve every `blocking:` unknown.
4. Validate the Profile and existing Guards with `make check-ai-project-profile` and `make check-ai-guard-calibration`.
5. Replace every placeholder in `Makefile.ai.stack` and confirm `make quality` passes.
6. Review the Coverage paths, then set `adoptionReviewed: true`.
7. Configure CI to fetch full Git history and run `make check-ai-pr AI_BASE_COMMIT=<merge-base-sha>` and `make quality` as independent required checks.
8. Run `make check-ai-adoption-ready` to verify static configuration completeness.

Doctor is read-only apart from its report under `target/`. Calibration writes only `.ai/project_profile.proposed.yaml` and never overwrites Guards. The confirmed Project Profile is project-owned and preserved across upgrades. `make check-ai-adoption-ready` is fail-closed, but neither Profile approval nor readiness is a security proof. Require successful `make quality` and `check-ai-pr` runs as independent CI checks.
