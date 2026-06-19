---
author: Ray
title: "Adoption Readiness"
description: Installed, repository-local guidance for completing AI Cockpit adoption.
---

# Adoption Readiness

Installation deploys the governance runtime. It does not prove that project-specific quality commands, Coverage Guard paths, or pull-request CI are correct.

Before making AI Cockpit a required production gate:

1. Replace every placeholder in `Makefile.ai.stack` and confirm `make quality` passes.
2. Review the `production.include`, `production.exclude`, and `tests.include` paths in `.ai/guards/coverage_policy.yaml`, then set `adoptionReviewed: true`.
3. Configure CI to fetch full Git history and run `make check-ai-pr AI_BASE_COMMIT=<merge-base-sha>` and `make quality` as independent required checks.
4. Run `make check-ai-adoption-ready` to verify static configuration completeness.

`make ai-doctor` is advisory diagnostics. `make check-ai-adoption-ready` is a fail-closed static configuration gate: it detects missing placeholders, explicit Coverage review, and CI wiring, but it cannot prove that arbitrary project commands are meaningful. Require successful `make quality` and `check-ai-pr` runs as independent CI checks.
