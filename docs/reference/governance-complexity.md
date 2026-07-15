---
author: Ray
title: Governance Complexity and Archive Lifecycle
description: How maintainers measure governance growth without rewriting immutable audit history.
keywords:
  - governance
  - archive
  - complexity
---

# Governance Complexity and Archive Lifecycle

Run `make check-governance-complexity` during maintenance and before a release. The check writes `target/governance_complexity_report.json` and reports tracked-file count, Python/Markdown line counts, archive Contract/Summary counts, and archive index consistency.

Thresholds live in `.ai/guards/governance_complexity_policy.yaml`. A threshold change requires a Work Item explaining the new repository shape and the expected reviewer impact. The report is intentionally read-only: it detects growth but does not delete or rewrite historical evidence.

## Lifecycle rules

- Archived Contract and Summary files are immutable audit records.
- Every archived Contract must have a paired Summary. The discovery index must not contain dangling or malformed Contract/Summary references; legacy records may remain outside the maintained index.
- Review the report quarterly and whenever archive growth approaches a configured limit.
- A future compaction proposal must preserve the original files, retain an index mapping, and receive a separate reviewed Work Item.
- Prefer reducing new governance artifacts and improving summaries over deleting history.
