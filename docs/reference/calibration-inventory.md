---
author: Ray
title: Calibration Inventory
description: Shared evidence matrix for calibration and adoption readiness.
keywords:
  - calibration
  - inventory
  - evidence-governance
  - readiness
---
# Calibration Inventory

`scripts/ai_calibration_inventory.py` is the shared fact source for calibration, adoption readiness, and generated Cockpit Status. It does not turn static file presence into proof that a project command, external CI run, or human review occurred.

Generate or validate an inventory with:

```sh
make cockpit-calibration-inventory ARGS="--output target/calibration-inventory.json --check"
```

Every inventory contains these ten boundaries, in stable order:

`profile`, `guards`, `quality`, `coverage`, `complexity`, `review`, `security`, `ci`, `installed_lifecycle`, and `documentation`.

Each item records:

- `status`: exactly one of `complete`, `warning`, `incomplete`, `unknown`, or `not_applicable`.
- `source`: the authoritative file, command, run, or evidence reference.
- `confirmation`: `none`, `static`, `command`, `human`, or `external`.
- `evidence`: concrete evidence references; an empty list is not a passing result.
- `staleAt`: an ISO timestamp or `null`; expired evidence cannot remain `complete`.
- `owner`: the project or person responsible for the evidence.
- `blockingReason`: why a reviewer must investigate, confirm, or stop.

`readiness_state()` exposes the same object as `calibrationInventory`, while retaining compatibility fields for existing callers. Generated `current_status.md` renders the same statuses and provenance. A static `warning` or `not_applicable` result is deliberately different from a command-confirmed `complete` result; adopter readiness and production claims require the relevant runtime and external evidence separately.

The matrix is repository evidence, not an identity system, approval system, immutable audit ledger, sandbox, or enterprise assurance claim.
