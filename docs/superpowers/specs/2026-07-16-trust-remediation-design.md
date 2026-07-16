---
author: Ray
title: "Trust Remediation Design"
description: Design for closing the review's release and governance trust findings.
keywords:
  - trust
  - remediation
  - ai-cockpit
---

# Trust Remediation Design

## Goal

Resolve the review's remaining trust blockers in dependency order, while keeping the next release as the final, separately verified action.

## Work-item decomposition

The remediation is split into nine implementation Work Items: canonical repository identity; workflow-generated provenance; adoption readiness; archive integrity; one Work Item/one PR enforcement; strict closure validation; delegated secret scanning; compatibility baseline/latest separation; and base-branch discovery. A tenth release Work Item is intentionally deferred until all nine are verified.

Each Work Item has its own Contract, branch, tests, Summary, and PR evidence. No Work Item edits archived evidence from another Work Item.

## Design decisions

1. The canonical source is `spirex-ds-dev/ai-cockpit-template`. Explicit overrides remain supported, but defaults, documentation, and release checks must identify the canonical source.
2. Final provenance is produced by the release workflow for an immutable source commit and published as release evidence. Repository-tracked files are candidate baselines only.
3. Adoption readiness fails closed when CODEOWNERS or SECURITY.md is absent, placeholder-based, or structurally incomplete.
4. Archive indexes are integrity manifests, not labels: hashes, coverage, uniqueness, and strict pair validation are checked at read time.
5. The PR gate accepts one newly added Contract/Summary pair by default. Exceptions are explicit and auditable.
6. Legacy summary validation is limited to archives identified by the migration predicate.
7. Secret detection remains a fast local guard; CI delegates full-history and provider-specific detection to maintained tools.
8. Compatibility evidence is split into reproducible release baselines and non-blocking latest-ecosystem probes.
9. Base branch discovery is centralized so finish and close use the same remote/default-branch identity.

## Verification strategy

Every behavior change starts with a failing regression test, then a minimal implementation, focused tests, and the repository's required `make` gates. The release Work Item additionally verifies the published tag, source commit, provenance subject, digest, SBOM, and distribution smoke evidence.
