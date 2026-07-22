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

The release workflow treats committed `.ai/cockpit/sbom.json`, `provenance.json`, and `release-digests.json` as candidate baselines only. `release.json` declares `releaseEvidenceAuthority: release-assets-v1`, so the public checker must inspect the published Release Assets before accepting final evidence. After checking out the immutable `SOURCE_COMMIT`, it runs `check_supply_chain.py release-assets`, verifies that every generated provenance and digest subject names that exact commit, runs strict Smoke for that source commit, and only then creates the tag and Draft Release. The Draft Release is published only after tag-target and asset-subject verification. Candidate provenance from a previous public release must not be treated as final proof for the current release because it was created before this source-bound asset flow.

## PR-first release sequence

Changes enter `main` through a pull request. Both `smoke` and `compatibility` also run on `main` pushes, so the commit selected for release has fresh repository-level and cross-platform evidence. Maintainers dispatch `.github/workflows/release.yml` with a new tag and the exact verified default-branch SHA. The workflow resolves the remote symbolic `HEAD`, fetches `origin/<default-branch>`, and rejects a feature-branch or ambiguous source. It records Source Commit, Remote, Default Branch, and Run ID in `release-source.json`, rejects existing tags, requires successful smoke and compatibility runs for that SHA, verifies `release.json`, and only then creates the tag and GitHub Release.

The historical release tag is immutable evidence and is not rewritten. A release-preparation PR may declare exactly the next patch tag as pending publication; it must pass local metadata and evidence checks without claiming that the public tag already exists. After the PR merges, maintainers dispatch `.github/workflows/release.yml` with the exact verified `main` SHA. That workflow creates the immutable tag and GitHub Release, then dispatches a strict smoke verification against the now-public release. The workflow requires `release.json.releaseTag` to match the requested tag.

This release flow applies to the template repository. An adopter project must create its own installation or upgrade branch from its own remote default branch and consume the published release tag. The adopter's installation or upgrade is a separate Work Item and PR in the adopter repository; it does not branch from the template repository's `main` or share the template release PR.

## Archive evidence index

`archive/index.json` is an additive discovery index maintained by `archive-work-item`. It records each Work Item's identity, archive sequence, relative Contract/Summary paths, and file hashes so tooling can discover historical evidence without parsing every Summary. The archived Contract and Summary remain authoritative; the index is disposable and may be rebuilt from them if needed.

The development lock is generated from the committed `requirements-dev.in` input with `pip-compile --generate-hashes --allow-unsafe`. The SBOM reports workflow Action occurrences, all version-pinned lock entries, and the direct/transitive split recorded by pip-compile's `via` annotations. Every locked package must carry at least one SHA-256 artifact hash; CI installs with `pip install --require-hashes` so an unlisted artifact fails closed.

The published `release-digests.json` also contains one correlation record. It records the workflow Run ID, workflow Run SHA, source commit, release tag, and the generated SBOM/provenance digests. The release workflow and public distribution checker reject missing Run IDs, Run SHA or tag mismatches, and artifact digest mismatches before tag or publication mutations are accepted. Evidence from another run or source commit must not be mixed into a release.
The generated `.ai/cockpit/release-digests.json` manifest binds the lock, SBOM, provenance, installer, and release metadata to one source commit and records their SHA-256 digests. `make check-release-evidence` verifies that binding and fails on drift.
The release workflow also runs `make check-lockfile-reproducibility`, which regenerates the hash-enabled lock from `requirements-dev.in` and fails on byte drift before publication. The Make target invokes `$(PYTHON) -m piptools compile` through the interpreter selected by the repository (`.venv/bin/python` when present, otherwise `python3`); it does not assume that a `pip-compile` executable exists beside that interpreter. The blocking compatibility workflow runs the same target on a clean Ubuntu runner after installing pip-tools, so missing lockfile-tool dependencies or regenerated lockfile drift are visible as explicit failures.

When `releaseEvidenceAuthority` is `release-assets-v1`, the public checker downloads `sbom.json`, `provenance.json`, and `release-digests.json` from the tagged GitHub Release. It validates source-bound SBOM/provenance hashes from the published manifest and exact tag/commit identity; those volatile assets are intentionally allowed to differ from candidate baselines committed before the immutable source SHA existed. Stable artifacts remain rehashed from the tag tree, and missing, altered, malformed, unsafe, cross-tag, or cross-commit evidence is rejected before exercising the installer.
Compatibility support claims are split between a fixed-version blocking baseline and separately reported hosted ecosystem probes. The baseline pins Python 3.10/3.11/3.14, Go 1.24.4, Rust 1.86.0, Node 24.11.1, Java 21, Ruby 3.4.2, PHP 8.4, Gradle 8.12, and the declared mobile fixture levels; it runs on the `ubuntu-latest` and `macos-latest` labels where applicable. Only that baseline is release-blocking. The `latest-ecosystem-probe` lane requests current Stable/Latest tools and is explicitly non-blocking; its result is exploratory evidence and must not be described as verified baseline support. Hosted labels can move independently of the pinned tool versions, so Ubuntu/macOS image changes remain an external compatibility risk.

## Published Capabilities

The documented public release is defined in `release.json`. Release preparation may use the separate `next-release.json` candidate record, which must be marked `releaseState: candidate`, `published: false`, and exactly one patch after the published tag. Quick Install and installer source metadata consume only `release.json`; the candidate record cannot redirect the public installation entry. Release preparation validates the candidate record; the publication workflow rewrites no candidate evidence and publishes only after exact-source verification.

Release progression has one canonical record: `release-state.json` (`schemaVersion: 1`, `canonical: true`). It owns the `development` → `candidate_prepared` → `candidate_verified` → `release_published` state machine, release tag, previous release, source identity, and evidence references. `release.json` and `next-release.json` are explicitly declared projections: the former is the published installer contract and the latter is the unpublished candidate projection. They are not independent release truths. `evidenceStatus` describes whether provider evidence is pending, verified, or published; `evidenceBundleDigest` is `null` until provider evidence exists and must be a real SHA-256 for verified or published states. `make check-release-state-consistency` rejects missing canonical markers, projection remapping, prose placeholders, and invalid status/digest combinations. Failed verification must leave the state and tag unchanged.

Installer and upgrade flows intentionally exclude the template's `sbom.json`, `provenance.json`, and `bandit_low_risk_baseline.json`. Those files describe the template release; an adopter must generate and verify project-owned evidence after adoption.

- Public releases can verify the installer archive when `AI_COCKPIT_TEMPLATE_SHA256` is provided and supported by the published release metadata.
- `make check-release-distribution` validates the documented distribution contract against the real installer.
- Worktree capabilities are only public when the installed release passes the published distribution check.
- The repository also maintains supply-chain evidence checks for the dev dependency lockfile, SBOM/provenance baselines, and secret scanning. The local `make check-secret-scanning` command is a fast lightweight guard over the current checkout. The release-blocking `smoke` workflow additionally builds and runs Gitleaks from a pinned upstream commit over the full checkout history as delegated evidence; the repository does not claim that local pattern matching replaces professional secret-scanning coverage or that GitHub Secret Scanning is enabled by repository content alone.

The digest manifest proves repository-internal consistency only. The project does not currently publish trusted archive checksum files, cryptographic signatures, or provenance attestations; a release pipeline must provide an independently verifiable signature or Sigstore/provenance attestation and publish its verification material. Treat caller-provided SHA256 comparison and this manifest as additional checks, not as an external trust root.
An unreleased worktree may regenerate its local SBOM, provenance, and digest manifest before the next public tag. `check-release-distribution` validates the historical tag's own evidence separately and does not equate those unreleased digests with the tag's public claims.

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
## Next release candidate

The candidate records a preparation snapshot, but the release workflow resolves `SOURCE_COMMIT` from the freshly fetched default branch at dispatch time. An omitted `source_commit` input uses that resolved commit; a supplied value is only an assertion and must match it exactly. Detached checkout, tag, provider workflow, SBOM, provenance, and digest evidence must all reference that same immutable source before promotion. A stale or mismatched assertion fails closed before checkout or publication. Missing provider assets remain missing evidence; this release does not change the enterprise-security NO-GO boundary.
