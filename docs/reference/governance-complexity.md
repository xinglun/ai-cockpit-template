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

Run `make check-governance-complexity` during maintenance and before a release. The check writes `target/governance_complexity_report.json` and reports tracked-file count, Python/Markdown line counts, archive Contract/Summary counts, and archive index consistency. Archive counts are observational metrics; they are not cumulative blocking limits.

Thresholds live in `.ai/guards/governance_complexity_policy.yaml`. A threshold change requires a Work Item explaining the new repository shape and the expected reviewer impact. Live repository thresholds remain blocking; archive totals are intentionally observational. The report is intentionally read-only: it detects growth but does not delete or rewrite historical evidence.

The Python threshold is calibrated at 24,050 for the lifecycle-enforcement Work Item because the repository gained the explicit finish-versus-closure guard, its regression coverage, and the associated governance checks. This is a small capacity adjustment with no change to archive integrity policy; future growth remains blocking and requires another documented Work Item.

## Lifecycle rules

- Each pull request must contain one newly maintained Work Item archive pair; combine independent Work Items in separate pull requests.

- Archived Contract and Summary files are immutable audit records.
- Every archived Contract must have a paired Summary. The discovery index must cover each pair exactly once and must not contain dangling or malformed Contract/Summary references.
- Index work-item identities, archive sequences, and SHA-256 digests are checked against the authoritative files; tampering, duplicate claims, missing entries, or path drift are blocking failures. Legacy records may remain readable, but they cannot weaken current index integrity.
- Newly changed archive evidence must be attributed to the current Work Item by `make check-ai-pr`; historical archive totals do not establish current-task ownership.
- Review the observational archive counts quarterly as a repository-maintenance signal, not as a gate on unrelated current Work Items.
- A future compaction proposal must preserve the original files, retain an index mapping, and receive a separate reviewed Work Item.
- Prefer reducing new governance artifacts and improving summaries over deleting history.
