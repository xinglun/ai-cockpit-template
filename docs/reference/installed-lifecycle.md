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

Use `make ai-cockpit-version` for the installed version and `make ai-cockpit-update-check TARGET_VERSION=vX.Y.Z` for a read-only update check. Both commands consume validated facts, report `readOnly: true`, and return an error state without writing files when facts or Release Evidence are missing or invalid.

## Three-way update proposals

Before any update is applied, generate a reviewable proposal from the installed baseline (Old Template), candidate release (New Template), and current project:

```text
make ai-cockpit-update-propose OLD_TEMPLATE=/path/to/old NEW_TEMPLATE=/path/to/new UPGRADE_ID=upgrade-2026-07
```

The proposal is written only to `.ai/upgrade/proposals/<upgrade-id>.json`; generation does not modify Runtime or project files. Each change is classified as an unchanged or safe template update, project-modified conflict, project-owned file, shared managed region, new/removed template file, generated file, historical file, or fail-closed conflict. The proposal also binds installed and candidate manifest hashes, Release Evidence, rollback baseline, migration and documentation impact, and a resume condition. Safe files may be considered by the later confirmation/apply Work Item, while project-owned, shared, historical, generated, and removed content requires explicit review.

Apply is a separate confirmation boundary:

```text
make ai-cockpit-update-apply PROPOSAL=.ai/upgrade/proposals/upgrade-2026-07.json
make ai-cockpit-update-apply PROPOSAL=.ai/upgrade/proposals/upgrade-2026-07.json CONFIRM=APPLY
```

The first command is read-only and returns the confirmation options. The confirmed command checks repository drift, creates `.ai/upgrade/snapshots/<upgrade-id>/`, applies only safe/new files, retains project-owned and historical content, updates validated facts, and writes an ordered Update Summary. Drift or unresolved conflicts stop before any write. Migration, generated regeneration, readiness, and smoke-test steps remain explicit deferred stages for their dedicated Work Items.

## Schema migration

Project-owned configuration migrations use a versioned registry and produce a plan containing old/new fields, defaults, non-migratable content, policy impact, and reconfirmation items. Policy strengthening, critical-threshold changes, baseline changes, and other high-risk changes return `needs_human_confirmation`; unsupported reverse migrations return `partial_rollback` and do not write configuration. The migration planner is `scripts/ai_schema_migration.py` and is intentionally separate from update application.

## Rollback snapshot and execution

## Disable and enable

Disable is a reversible state transition, not uninstall: it records disable evidence, sets `disabled`, and adds a blocking entry while retaining Runtime, Policy, Evidence, Archive, Update, Uninstall, and CI managed-region content. It does not silently remove a CI Gate. Enable rechecks Runtime Integrity, Manifest, Project Profile, Policy, and Adoption Readiness; any failed check leaves the installation disabled with a resume condition. Only when all checks pass is the state changed back to `active`.

## Uninstall proposal and preserve-evidence mode

Phase A is a read-only proposal boundary with three explicit modes: `disable`, `preserve-evidence`, and `purge`. The default `preserve-evidence` mode requires drift and Ownership checks, exports an evidence bundle, and hands off to a detached uninstaller; it retains Bootstrap Evidence, Archive, Human Decisions, Project Policy, Complexity Baseline, Audit Evidence, and project-owned files. Modified Template/Shared content, unknown Ownership, or drift blocks the proposal. `purge` remains destructive and confirmation-gated, with an explicit deletion list, export requirement, and final receipt.

The detached uninstaller runs from `<system-temp>/ai-cockpit-uninstall/<session-id>/uninstall.py` and must not import the object project Runtime. It performs Drift Check → confirmed Runtime removal → Managed Region handling → evidence retention → final Receipt → Runtime Removal Verification. Unconfirmed, modified, or unknown-owned files remain untouched; the receipt records removed files, preserved business/evidence files, and verification state.

Before an update mutates Runtime or Managed Regions, a snapshot is created under `.ai/upgrade/snapshots/<upgrade-id>/`. It contains `manifest.before.json`, `version.before.json`, `managed-regions.before.json`, Runtime restore sources, the Project Config hash, the Migration Plan, and rollback instructions. Rollback first validates the current installed manifest, then emits a confirmation-gated proposal. Confirmation restores only snapshot-owned Runtime and Managed Region content; Project-owned code and configuration are preserved even when they drifted after the update. Missing snapshots or current-installation drift are `blocked`. A non-invertible migration is `partial_rollback` and lists remaining manual operations; no write occurs in either state.
