---
author: Ray
title: "Adoption Readiness"
description: Installed, repository-local guidance for completing AI Cockpit adoption.
---

# Adoption Readiness

[日本語](adoption.ja.md)

Installation deploys the governance runtime. It does not prove that project-specific quality commands, Coverage Guard paths, or pull-request CI are correct.

AI Cockpit fits a **generic template plus local calibration** model: installation is feasible, but production readiness requires a separate `configure_ai_cockpit` Work Item after adoption.

First adoption with `--create-adoption` is transactional: validation finishes before branch mutation, `--dry-run` performs no Git fetch or branch changes, and a failed install restores the original branch or detached HEAD together with the filesystem. Successful adoption still requires the human-approved finish, PR, and close flow below—it is not release or external-review readiness. Template supply-chain evidence files (`.ai/cockpit/release-digests.json`, `.ai/cockpit/sbom.json`, `.ai/cockpit/provenance.json`) are not copied to the adopter tree; they record digests and attestations for template release artifacts that are not meaningful outside the template repository.

The installed Cursor rule (`.cursor/rules/ai-cockpit.mdc`) defaults to `alwaysApply: false`. Enable **Always Apply** when you want Work Item governance on read-only investigation too.

Before making AI Cockpit a required production gate, run the guided flow:

```sh
make ai-onboard
```

Or follow the local calibration checklist:

1. **Adopt, then configure:** finish `adopt_ai_cockpit` in one commit, then start `configure_ai_cockpit` for Profile, Guard, quality commands, and CI.
2. Run `make cockpit-doctor` to record project facts, evidence, confidence, candidate boundaries, Guard mismatches, and unknowns. Resolve every `blocking:` unknown in the confirmed Profile; doctor does not auto-approve boundaries.
3. Run `make cockpit-calibrate`. Review the proposed Profile without treating suggestions as approvals.
4. Create `.ai/project_profile.yaml` with explicitly confirmed boundaries and approval metadata.
5. Validate the Profile and existing Guards with `make check-ai-project-profile` and `make check-ai-guard-calibration`.
6. Replace every placeholder in `Makefile.ai.stack` and confirm `make ai-cockpit-quality` passes.
7. Review Coverage paths. For legacy or broad trees, start with `reportOnly: true` and narrowed include/exclude paths, then set `adoptionReviewed: true` when boundaries are stable.
8. **Staged CI:** configure **L1** first—full Git history plus `make check-ai-pr`. After L1 is stable, add **L2** `make ai-cockpit-quality` as a separate required job.
9. Run a pilot Work Item if needed with quality optional, then promote quality and Coverage to blocking gates.
10. Run `make check-ai-adoption-ready` to verify static configuration completeness.

Doctor is read-only apart from its report under `target/`. Calibration writes only `.ai/project_profile.proposed.yaml` and never overwrites Guards. The confirmed Project Profile is project-owned and preserved across upgrades. `make check-ai-adoption-ready` is fail-closed, but neither Profile approval nor readiness is a security proof. Require successful `make ai-cockpit-quality` and `check-ai-pr` runs as independent CI checks.
