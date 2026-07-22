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

Run `make check-governance-complexity` during maintenance and before a release. The check writes `target/governance_complexity_report.json` and reports Python/Markdown lines, maximum per-function complexity, Trust schema count, guard count, repeated protocol fields, dependency cycles, installer allowlist entries, archive growth, generated-evidence ratio, archive Contract/Summary counts, and archive index consistency. Use `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/ai_archive_work_item.py --rebuild-index` when a historical index needs to be regenerated from authoritative archive pairs; this command only updates the generated discovery index. An index repair is a restricted, explicitly approved Work Item change; Contract/Summary evidence remains append-only.

Thresholds live in `.ai/guards/governance_complexity_policy.yaml`. A threshold change requires a Work Item explaining the new repository shape and the expected reviewer impact. Every increase must have a `repaymentRecords` entry with the prior limit, new limit, accountable owner, due date, and concrete reduction plan; an increase without that record fails closed. Budgets enforce limits; they are not a record of why complexity was added. WI10 repays measured Python growth by moving the installer catalog to data and establishing tested installer boundaries without raising the ceiling. Archive growth remains observable, while Archive Index integrity is blocking. The report is intentionally read-only: it detects growth and missing, duplicated, or hash-mismatched index evidence but does not delete or rewrite historical evidence.

New archive rows carry strict hash, path, Work Item identity, and sequence checks; historical rows remain readable under the documented legacy boundary. The boundary is row-owned: a positive sequence together with both immutable digests enables strict validation. It is not selected by an editable global sequence cutoff. Future growth remains blocking and requires another documented Work Item.

## Lifecycle rules

- Each pull request must contain one newly maintained Work Item archive pair; combine independent Work Items in separate pull requests.

- Archived Contract and Summary files are immutable audit records.
- Every archived Contract must have a paired Summary. The discovery index must cover each pair exactly once and must not contain dangling or malformed Contract/Summary references.
- Index work-item identities, archive sequences, and SHA-256 digests are checked against the authoritative files; tampering, duplicate claims, missing entries, or path drift are blocking failures. Legacy records may remain readable, but they cannot weaken current index integrity.
- Newly changed archive evidence must be attributed to the current Work Item by `make check-ai-pr`; historical archive totals do not establish current-task ownership.
- Review the observational archive counts quarterly as a repository-maintenance signal, not as a gate on unrelated current Work Items.
- A future compaction proposal must preserve the original files, retain an index mapping, and receive a separate reviewed Work Item.
- Prefer reducing new governance artifacts and improving summaries over deleting history.
