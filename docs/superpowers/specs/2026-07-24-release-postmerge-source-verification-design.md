---
author: Ray
title: "Release Candidate-to-Merge Source Verification Design"
description: Separate premerge candidate content from post-merge exact source identity.
keywords:
  - release
  - preflight
  - source-identity
  - candidate-merge
---

# Release Candidate-to-Merge Source Verification Design

## Goal

Prevent a release-preparation pull request from passing with archive evidence
calculated from the old default branch, then failing only after its candidate
content is merged. The corrected process must verify the real transition from
candidate commit to merged default-branch commit before any tag or GitHub
Release mutation.

## Evidence and root cause

The v0.5.39 failure is reproducible on `6c0b8a52`:

- old default-branch commit `3bf48347` produces archive `23cb9fc8...`;
- PR candidate `f1faf013` produces archive `b13cc3d2...`;
- merge commit `6c0b8a52` also produces archive `b13cc3d2...`.

The merge did not change canonical archive content. Premerge finalization
hashed the old `origin/main` commit instead of the candidate branch HEAD.
Commit `1aa92bec` had previously separated candidate materialization from
controlled identity resolution, but `dee86e44` reverted that behavior and
changed the unit expectation to the stale default-branch commit. PR-local
tests therefore agreed with the defective implementation.

## Selected architecture

Candidate content and published identity are separate boundaries:

1. Premerge finalization runs on a clean, dedicated Work Item branch after
   archive. It materializes `sourceTree` and `archiveSha256` from that branch's
   concrete `HEAD`.
2. Committed freeze metadata retains a controlled default-branch identity
   reference such as `origin/main`. It does not claim to know a future merge
   commit SHA.
3. After PR merge, Work Item closure, and default-branch synchronization, the
   hosted release workflow resolves the unique remote default branch exactly
   once and checks out that commit detached.
4. Release preflight recalculates the canonical tree and archive from the
   merged commit. They must equal the candidate freeze values.
5. The workflow emits exact `sourceCommit`, `tagTarget`, and `metadataCommit`
   values in provider-generated `release-source.json`. This avoids the
   impossible requirement for a Git commit to contain its own SHA.
6. Any mismatch stops before dependency installation, tag creation, or release
   publication and returns the work to a corrective process Work Item.

The existing release workflow already implements steps 3 and 5. The required
code correction is the candidate materialization source in
`finalize_release_freeze.py`, backed by a topology-level regression.

## Components

### Premerge finalizer

`scripts/finalize_release_freeze.py` keeps the controlled identity tuple for
post-merge resolution but passes the clean candidate `HEAD` to the canonical
archive builder in premerge mode. Other modes retain their current behavior.

### Post-merge preflight

`scripts/check_release_preflight.py` remains the fail-closed verifier. It
resolves controlled identity fields, requires them to match the explicit
merged source commit, and recalculates the source tree and archive from that
commit.

### Provider identity evidence

`.github/workflows/release.yml` remains the authority for the exact merged SHA.
It discovers the unique default branch, rejects a stale caller assertion,
checks out the resolved commit detached, creates `release-source.json`, and
runs preflight before tag mutation.

## Regression strategy

The regression must create real Git topology rather than mock commit labels:

1. initialize a source repository with release fixtures and a base commit;
2. create a candidate branch with included source changes and export-ignored
   Work Item/release metadata;
3. run premerge finalization on the candidate while `origin/main` still names
   the base;
4. create a no-ff merge commit whose canonical content equals the candidate;
5. fetch the merge commit as `origin/main` into a fresh repository;
6. check out the merge commit detached and run explicit-source preflight;
7. assert the exact merged SHA and successful preflight;
8. change included canonical content and assert preflight fails.

The focused unit assertion must also require premerge finalization to call the
canonical builders with candidate `HEAD`, not `origin/main`.

Archive growth is independently checked with warning enforcement so counts at
538 or higher remain diagnostic rather than blocking.

## Lifecycle and error handling

The corrective Work Item follows one branch and one PR:

```text
latest origin/main
→ Contract and Preflight
→ red regression
→ minimal correction
→ green focused/full checks
→ ai-finish and archive
→ check-ai-pr
→ push and PR
→ merge
→ ai-close-work-item
→ synchronized main
→ exact-SHA smoke, compatibility, and release preflight
→ v0.5.39 release workflow
```

No release metadata-only PR is allowed without an owning Contract. A failed
post-merge verification is treated first as a process defect; publication is
not retried until its executable gate is corrected.

## Non-goals

- committing an exact SHA into the commit whose identity it would define;
- weakening identity, archive, lifecycle, or PR ownership checks;
- changing adopter-project release semantics;
- creating or moving v0.5.39 during the corrective Work Item.
