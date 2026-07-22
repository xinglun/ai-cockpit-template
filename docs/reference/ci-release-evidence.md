---
author: Ray
title: "CI and Release Evidence"
description: Independently verifiable CI and release evidence contract.
keywords:
  - ai-cockpit
  - ci
  - release
  - evidence
---

# CI and Release Evidence

CI/Release Evidence is a provider-derived JSON record. Its authority is GitHub Actions or the GitHub API, never a pull-request description, agent message, or other self-declared “passed” claim. The validator is `scripts/check_ci_release_evidence.sh`; `make check-ci-release-evidence CI_RELEASE_EVIDENCE=<path>` is the local entry point.

Every record binds a Workflow Run ID, Head SHA, Required Job Names, per-job Conclusions, overall Conclusion, failure reasons, artifact digests, SBOM, Provenance, and a Head-to-Merge relationship. A verified or published record must also bind a merge commit, successful required jobs, empty failure reasons, and non-null SBOM/Provenance digests whose source commit equals the Head SHA. Missing or cross-source identity fails closed.

The state boundary is explicit:

- `candidate` records describe CI evidence for a change or release candidate and may omit release-only SBOM/Provenance assets.
- `verified` records are provider evidence for an exact source commit after required jobs and release assets have passed.
- `published` records are verified evidence attached to the immutable public release.
- `failed` records must include failure reasons; they cannot authorize a verified or published state.

The smoke workflow emits a structured candidate/failed record to its workflow log and validates it independently. The release workflow obtains exact-SHA smoke and compatibility run records through the provider API, produces `ci-release-evidence.json`, validates it, and publishes it as a release asset. The canonical `release-state.json` rejects `candidate_verified` and `release_published` states without provider-bound `ciEvidence`. Local fixtures are regression inputs only and cannot prove a public release.

For pull requests, the evidence records the PR Head SHA and explains how the provider-side merge commit relates to that head. For release dispatch, the source is resolved from the remote default branch and the merge commit is the exact release source. No PR Body text is parsed or accepted as evidence.
