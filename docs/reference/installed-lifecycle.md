---
author: Ray
title: "Installed Lifecycle Facts"
description: "The durable installation facts used by later governed lifecycle operations."
keywords:
  - installed-lifecycle
  - manifest
  - ownership
  - rollback
---

# Installed Lifecycle Facts

Every fresh AI Cockpit installation records its durable lifecycle facts under `.ai/install/`:

- `manifest.json` records the installation identity, source/version, timestamp, installed paths, source paths, ownership class, and SHA-256 digest.
- `version.json` records the installed distribution and Contract schema versions, Runtime State, and the SHA-256 binding to the manifest.
- `managed-regions.json` records Shared files and their installation-time full-file boundaries. Later Work Items may add explicit managed regions without guessing from paths.
- `rollback-baseline.json` records the installation-time digest baseline used by later update and rollback proposals.

Ownership is explicit: `template`, `project`, `shared`, `generated`, or `historical`. The installer does not infer permission to overwrite or delete project-owned or historical content from a path alone. `scripts/ai_install_facts.py` validates that all fact files exist, agree on one installation identity, and match the installed file digests; missing, malformed, or tampered facts fail closed.

These facts are a repository record, not an identity system, approval system, immutable audit ledger, sandbox, or enterprise assurance claim. Update, migration, rollback, disable/enable, uninstall, and purge behavior is governed by their own Work Items and must consume validated facts.

## Ownership decisions

Ownership is an installation fact, not a path heuristic. The supported classes are:

- `template`: distributed content that may be refreshed by a governed update.
- `project`: adopter configuration or business content that is preserved by default.
- `shared`: files that may change only inside explicit managed regions.
- `generated`: lifecycle-generated runtime or status content.
- `historical`: archived evidence that is immutable and never overwritten.

Shared regions use matching markers such as `# BEGIN AI COCKPIT MANAGED REGION: ci` and `# END AI COCKPIT MANAGED REGION: ci`. Missing, duplicate, nested, unmatched, or drifted markers produce a fail-closed decision. Unknown ownership, project content, and historical evidence are never mutation-authorized by the ownership evaluator.
