---
author: Ray
title: "Distribution"
description: Distribution and integrity reference for AI Cockpit.
keywords:
  - ai-cockpit
  - distribution
  - integrity
  - install
  - release
---

# Distribution

AI Cockpit distribution is versioned through the published installer and release metadata. Use this page when you need installer flags, integrity capabilities, or local-install details that do not belong in the main adoption flow.
The documented quick-install path resolves public release metadata first and then lets the installer use its own repo or source selection knobs. Public network access to the release metadata is required for that bootstrap step. Private or internally mirrored deployments should use the local-install or configured-source flow instead.

SBOM and provenance release evidence must be generated with an explicit source commit (`--source-commit` or `SUPPLY_CHAIN_SOURCE_COMMIT`). The local release-tag fallback exists only for compatibility and never derives evidence identity from the current `HEAD`.

The SBOM reports workflow Action occurrences and direct version-pinned lock entries. It marks transitive dependencies as `not_generated` unless a separate reproducible dependency export is supplied. The current lock file contains version pins, not per-artifact hashes, so it must not be described as equivalent to `pip install --require-hashes`.

## Published Capabilities

The documented release is defined in `release.json`.

Installer and upgrade flows intentionally exclude the template's `sbom.json`, `provenance.json`, and `bandit_low_risk_baseline.json`. Those files describe the template release; an adopter must generate and verify project-owned evidence after adoption.

- Public releases can verify the installer archive when `AI_COCKPIT_TEMPLATE_SHA256` is provided and supported by the published release metadata.
- `make check-release-distribution` validates the documented distribution contract against the real installer.
- Worktree capabilities are only public when the installed release passes the published distribution check.
- The repository also maintains supply-chain evidence checks for the dev dependency lockfile, SBOM/provenance baselines, and secret scanning.

The project does not currently publish trusted archive checksum files, cryptographic signatures, or provenance attestations. Treat caller-provided SHA256 comparison as an additional check, not as a published trust root.

## Installer Options

```text
--dry-run          Show actions without writing files.
--force            Overwrite existing AI Cockpit files.
--upgrade          Back up and replace managed runtime, policy, and agent marker files.
--upgrade-with-active
                   Permit a high-risk upgrade while active Work Item JSON exists.
--replace-glossary Back up and explicitly replace the project-owned .ai/glossary.md.
--create-adoption Create the first auditable adoption Work Item; requires clean committed Git state.
--with-examples    Copy examples/ into the target repository.
--update-makefile  Append "include Makefile.ai" to the target Makefile.
```

Without `--update-makefile`, the installer writes `Makefile.ai` and `Makefile.ai.stack` but does not modify the host `Makefile`.

## Local Install

From a local clone:

```sh
/path/to/ai-cockpit-template/install.sh --stack rust --update-makefile
```

## When To Use This Page

- You need the installed distribution behavior, not the adoption workflow.
- You need a canonical place for installer options and integrity notes.
- You are documenting release-specific distribution details for maintainers or integrators.
