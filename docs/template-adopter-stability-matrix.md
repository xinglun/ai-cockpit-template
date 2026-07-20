---
author: Ray
title: "Template and Adopter Stability Matrix"
description: Evidence matrix for template quality and imported-project governance.
keywords:
  - ai-cockpit
  - adoption
  - compatibility
  - stability
---

# Template and Adopter Stability Matrix

This matrix records which lifecycle claims have executable evidence. It is a governance aid, not a claim that every external adopter ecosystem has been validated.

| Layer | Scenario | Evidence | Boundary |
| --- | --- | --- | --- |
| Template | Python quality, security, supply-chain, and status checks | `make ai-cockpit-quality` and required CI checks | Template repository only |
| Compatibility | Supported stack matrix and smoke probes | `.github/workflows/compatibility.yml` | Matrix entries, not every project configuration |
| First adoption | Install, bootstrap, finish, and archive adoption Work Item | `tests/test_adoption_e2e.py` | Minimal generated adopter fixture |
| Governance journey | Configure profile, calibrate guards, run project checks, upgrade/rollback | `tests/test_project_governance_journey.py` | Minimal generated adopter fixture |
| Lifecycle | Branch, PR, merge, close, and cleanup | `make ai-close-work-item TASK=...` | Requires provider merge evidence and synchronized base |

The matrix must be updated when a lifecycle claim changes. Missing evidence is a gap to record, not a reason to infer stability from a successful template-only run.
