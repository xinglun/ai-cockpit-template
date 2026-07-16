---
author: Ray
title: "Conditional GO Remediation Cycle Implementation Plan"
description: Serialized execution plan for the Conditional GO remediation backlog.
keywords:
  - conditional-go
  - release-integrity
  - work-items
  - remediation
---
# Conditional GO Remediation Cycle Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Each child task is a separate Work Item with its own branch and PR.
**Goal:** Close the eight accepted P0/P1 findings from the Conditional GO review through an automatically advancing, fail-closed Work Item cycle.
**Architecture:** The cycle is a serialized queue, not one large branch. A controller starts exactly one child Work Item, runs its contract/checkpoint/verification/finish gates, waits for the PR merge and lifecycle closure, then starts the next child from the latest remote default branch. External approval and release publication remain explicit human gates.
**Tech Stack:** Python, Bash, GitHub Actions, Make, JSON Work Item Contracts, Markdown documentation, pytest.
## Global Constraints
- Preserve the repository rule: one Work Item, one dedicated branch, one PR.
- Start every child from the latest `origin/main`; record `baseCommit` in its Contract.
- Never create a second active Work Item while another child is active.
- Do not merge a feature branch into local `main` before its PR is merged.
- Run `make ai-close-work-item TASK=<task>` only after the PR is merged and archived.
- Stop and report `needs_human_confirmation` for platform permissions, protected review settings, release publication, or any failed preflight.
- A child is complete only when its required checks pass, its PR is merged, and lifecycle closure reports `ready for next Work Item`.
- The repository quality gate must report total test coverage of at least 85%; coverage exclusions or threshold reductions are prohibited.
- The new-version release is a human-gated production action and must not be represented as complete from local tests alone.
## Cycle Controller
The controller processes this queue in order:
```text
latest origin/main
  → create child Contract
  → ai-preflight
  → implement with TDD
  → child checks + ai-finish/archive
  → push + PR
  → wait for required review/CI and merge
  → ai-close-work-item
  → verify clean base
  → next child
```
The queue is:
1. `release_asset_authority_closure`
2. `release_asset_integrity_public_check`
3. `release_atomic_publication`
4. `lockfile_regeneration_gate`
5. `compatibility_probe_truthfulness`
6. `adoption_installer_transactionality`
7. `adopter_release_manifest_boundary`
8. `external_review_boundary_verification`
9. `quality_coverage_85_gate`
10. `publish_next_version`
11. `final_plan_document_cleanup`
For each child, run `make ai-preflight`, both required checkpoints, every Contract/Summary/Guard/Status/Ownership check listed in the Contract, `make quality`, and `make ai-finish TASK=<task>` after implementation. Keep the child active on any failure.
If any command fails, the controller keeps the child active, records the failure in its Summary, applies systematic debugging, and does not advance the queue. After merge and archive, it runs:
```bash
make ai-close-work-item TASK=<task>
git status --short --branch
git fetch origin
git diff --exit-code origin/main
```
### Task 1: Release Asset Authority Closure
**Work Item:** `release_asset_authority_closure`  
**Priority:** P0  
**Review mapping:** P0-1 and P0-2
**Files:**
- Modify: `release.json`
- Modify: `.github/workflows/release.yml`
- Modify: `scripts/check_release_distribution.py`
- Test: `tests/test_release_distribution.py`
- Test: `tests/test_workflows.py`
- Check generated evidence: `.ai/cockpit/provenance.json`, `.ai/cockpit/release-digests.json`
**Acceptance:**
- `release.json` explicitly selects `release-assets-v1` authority for public verification.
- The checker fails closed when Tag candidate identities disagree, unless the authoritative Release Assets prove the identity.
- Provenance commit, release tag, digest source commit, and Tag target must resolve to one exact source SHA.
- Tests cover the `v0.5.29`-style contradictory candidate case and the enabled authority path.
**Verification:** `pytest -q tests/test_release_distribution.py tests/test_workflows.py` plus the full cycle commands.
**Stop condition:** pause if the public Release API or asset download cannot be read with available credentials; do not downgrade to candidate-only validation.
### Task 2: Public Release Asset Integrity Check
**Work Item:** `release_asset_integrity_public_check`  
**Priority:** P0  
**Review mapping:** P0-4  
**Depends on:** Task 1
**Files:**
- Modify: `scripts/check_release_distribution.py`
- Test: `tests/test_release_distribution.py`
- Reference: `docs/reference/distribution.md`, `docs/reference/distribution.ja.md`
**Acceptance:**
- Downloaded `sbom.json`, `provenance.json`, and `release-digests.json` are hashed again after download.
- Every Manifest artifact digest is checked against the corresponding downloaded or Tag Tree content.
- `install.sh`, `release.json`, and `requirements-dev.lock` are checked against the Manifest and Tag target.
- Missing, altered, cross-tag, or cross-commit assets fail closed.
**Verification:** Add fixture tests for altered downloaded assets, altered Tag Tree files, and a fully valid asset set; run the focused distribution tests and `make quality`.
**Stop condition:** pause if the public asset naming or API contract differs from the documented release format; record the exact mismatch before changing the checker.
### Task 3: Atomic Release Publication
**Work Item:** `release_atomic_publication`  
**Priority:** P0  
**Review mapping:** P0-3  
**Depends on:** Tasks 1–2
**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `scripts/check_release_distribution.py`
- Modify: `install.sh`
- Modify: `README.md`, `README.zh-CN.md`, `README.ja.md`
- Test: `tests/test_workflows.py`, `tests/test_release_distribution.py`, `tests/test_installer.py`
**Acceptance:**
- A failed Tag Smoke cannot leave a semantically selectable release state.
- Publication occurs only after exact-ref Smoke and public asset verification succeed.
- Retry behavior is idempotent for failed or incomplete attempts.
- Quick Install fallback selects the highest published, non-Draft Release, never merely the highest `v*` Tag.
- Documentation describes the same atomicity boundary as the workflow.
**Verification:** Test success, Smoke failure, Draft Release, retry, and stale-tag scenarios; run the workflow regression suite and full quality checks.
**Human gate:** a real release or protected environment test may require a maintainer; do not publish a production tag automatically.
### Task 4: Lockfile Regeneration Gate
**Work Item:** `lockfile_regeneration_gate`  
**Priority:** P1  
**Review mapping:** P1-2  
**Depends on:** none
**Files:**
- Modify: `Makefile`
- Modify: `.github/workflows/quality.yml` or the workflow selected by the Make target
- Test: `tests/test_supply_chain.py`, `tests/test_workflows.py`
- Reference: `requirements-dev.in`, `requirements-dev.lock`
**Acceptance:**
- The quality gate regenerates `requirements-dev.lock` deterministically from `requirements-dev.in`.
- `git diff --exit-code requirements-dev.lock` fails when the committed lock is stale or manually altered.
- CI and local `make quality` invoke the same gate.
- The gate does not reintroduce `requirements-dev.txt`.
**Verification:** Test both a clean lock and an intentionally stale lock; run `make quality`.
**Stop condition:** pause if regeneration changes unrelated dependency versions; record the tool/version difference instead of accepting a broad lockfile churn.
### Task 5: Compatibility Probe Truthfulness
**Work Item:** `compatibility_probe_truthfulness`  
**Priority:** P1  
**Review mapping:** P1-1  
**Depends on:** Task 4
**Files:**
- Modify: `.github/workflows/compatibility.yml`
- Modify: `docs/reference/distribution.md`, `docs/configuration.md`
- Test: `tests/test_workflows.py`
- Modify toolchain fixtures only where required by the workflow
**Acceptance:**
- Blocking Baseline versions are explicit and reproducible for Python, Ruby, PHP, Swift, Ubuntu, and macOS lanes.
- `compatibility-latest` installs and runs actual Stable/Latest tools rather than replaying Baseline results.
- Latest probes are explicitly non-blocking and cannot be described as verified support.
- `ubuntu-latest`/`macos-latest` movement is documented as hosted-environment risk.
**Verification:** Workflow static tests assert distinct commands and dependencies; run local fixture checks and `make quality`.
**Stop condition:** pause if a stack cannot be pinned with the available package manager; mark that stack as an explicit external dependency rather than silently floating it.
### Task 6: Transactional Adoption Installer
**Work Item:** `adoption_installer_transactionality`  
**Priority:** P1  
**Review mapping:** P1-3  
**Depends on:** none
**Files:**
- Modify: `scripts/install_ai_cockpit.py`
- Test: `tests/test_installer.py`, `tests/test_adoption_e2e.py`
- Reference: `docs/getting-started/installation.md`, `.ai/cockpit/adoption.md`
**Acceptance:**
- `--dry-run --create-adoption` performs no fetch, branch creation, switch, or deletion.
- Managed conflict and Agent Marker validation happen before any branch mutation, or all mutation is transactionally rolled back.
- Rollback restores the exact original branch/HEAD state, including non-branch states where supported.
- E2E tests cover dry-run, marker failure, managed-conflict failure, runtime failure, and successful adoption.
**Verification:** Focused installer/E2E tests, then `make quality`.
**Stop condition:** pause if the original Git state cannot be restored without destructive behavior; require explicit human approval before changing rollback semantics.
### Task 7: Adopter Release Manifest Boundary
**Work Item:** `adopter_release_manifest_boundary`  
**Priority:** P1  
**Review mapping:** P1-4  
**Depends on:** Task 6
**Files:**
- Modify: `scripts/install_ai_cockpit.py`
- Modify: `docs/getting-started/installation.md`, `.ai/cockpit/adoption.md`
- Test: `tests/test_installer.py`, `tests/test_adoption_e2e.py`, `tests/test_adoption_ready.py`
**Acceptance:**
- Template `release-digests.json` is excluded from adopter-managed copy, alongside SBOM and Provenance.
- The resulting adopter tree contains no manifest that claims to prove artifacts absent from that tree.
- If a source reference is retained, its schema and filename explicitly identify it as a source-release reference.
- Adoption documentation and readiness checks use the same boundary.
**Verification:** Assert absence of the stale manifest in a synthetic adopter repository and run the adoption readiness and E2E suites.
### Task 8: External Review Boundary Verification
**Work Item:** `external_review_boundary_verification`  
**Priority:** P1 / human-gated  
**Review mapping:** P1-5  
**Depends on:** Tasks 1–3
**Files:**
- Modify only after maintainer approval: `.github/CODEOWNERS`
- Modify: `docs/getting-started/adopter-configuration.md`, `docs/configuration.md`
- Test/diagnostic: `scripts/ai_check_adoption_ready.py`, `tests/test_adoption_ready.py`
**Acceptance:**
- Repository documentation distinguishes self-declared Contract approval from trusted platform review.
- Adopter instructions require replacing placeholder ownership with an organization Team and at least two independent maintainers.
- Branch Protection or Ruleset evidence confirms required CODEOWNER review, stale-review dismissal, and conversation resolution.
- Release immutability claims are limited unless signed tags or independent attestations are actually configured.
**Human gate:** The agent must stop before changing the real owner or platform settings until an authorized maintainer supplies the organization Team and confirms platform access. This task cannot be marked complete from repository files alone.
**Verification:** Run readiness diagnostics and capture the platform API/Ruleset evidence in the Summary; if unavailable, mark the task `blocked_by_external_authority` and do not advance to a trusted-release claim.
### Task 9: Quality Coverage 85% Gate
**Work Item:** `quality_coverage_85_gate`
**Priority:** P1 release prerequisite
**Depends on:** Tasks 1–8
**Files:**
- Modify only the minimum required quality configuration and uncovered tests identified by the coverage report.
- Test: the affected `tests/**` files and the full repository quality suite.
- Reference: `Makefile`, `.ai/cockpit/checks.yaml`, `pyproject.toml` if coverage configuration is present.
**Acceptance:**
- `make quality` (or the repository's registered equivalent) passes with total measured coverage at or above 85.00%.
- New tests cover the highest-risk uncovered paths introduced or exposed by Tasks 1–8.
- No test, source path, or coverage omission is added solely to inflate the percentage.
- The threshold is recorded as a blocking release prerequisite in the Work Item Summary.
**Verification:** Run the full quality suite twice from a clean worktree and record the exact total coverage percentage, test count, and command output digest.
**Stop condition:** if coverage remains below 85%, do not advance to release; create focused tests or leave the cycle stopped with the measured deficit.
### Task 10: Publish Next Version
**Work Item:** `publish_next_version`
**Priority:** release gate
**Depends on:** Tasks 1–9
**Files:**
- Modify: `release.json` for the approved next semantic version.
- Modify only where required by the release workflow: `.github/workflows/release.yml`, release documentation, and generated release evidence.
- Test: `tests/test_workflows.py`, `tests/test_release_distribution.py`, and the exact release/Smoke checks.
**Acceptance:**
- The next version is explicitly selected and recorded; no version is guessed from the plan.
- Release assets are generated from one exact immutable source SHA.
- Compatibility, quality, exact-ref Smoke, Release Asset Authority, and public asset integrity checks all pass.
- The GitHub Release is published only after the required human approval and all blocking gates pass.
- The final Summary records the version, tag, source SHA, release URL, asset digests, Smoke run, and public checker result.
**Human gate:** A maintainer must approve the production publication and confirm the target repository/version. The agent may prepare and validate the release but must not silently publish an external release.
**Stop condition:** any failed Smoke, asset mismatch, missing platform approval, or ambiguous release identity stops the cycle and prevents Task 11.
### Task 11: Final Plan Document Cleanup
**Work Item:** `final_plan_document_cleanup`
**Priority:** final cleanup
**Depends on:** Tasks 1–10, including merged PRs and lifecycle closure
**Files:**
- Delete: `docs/superpowers/plans/2026-07-17-conditional-go-remediation-cycle.md`
- Preserve: `.ai/work-items/archive/2026/*.contract.json`, `.ai/work-items/archive/2026/*.summary.json`, and `.ai/work-items/archive/index.json`
**Acceptance:**
- All ten preceding child Work Items are archived and closed, with their PRs merged.
- The approved new version is published and independently verified.
- The plan Markdown is deleted from the final product branch.
- Archived Contracts, Summaries, status evidence, and index entries remain available for audit and are not deleted.
- The final cleanup Summary records the deleted path and confirms preserved evidence paths.
**Verification:** Run `git diff --check`, repository quality and governance checks after the deletion, then verify the archived evidence index still resolves every child Work Item.
**Stop condition:** never delete the plan document if any preceding Work Item is active, unmerged, unverified, or blocked by external authority.
## Completion Rule
The whole cycle is complete only when all eleven child Work Items are archived, their PRs are merged, `ai-close-work-item` has succeeded for each, total quality coverage is at least 85%, the new version is published and publicly verified, the final plan document is deleted, and the final base equals `origin/main`. The final report must list every child Contract, PR, merge commit, coverage result, release version/source SHA, verification result, cleanup evidence, and any remaining external-authority limitation.
The cycle must not report “enterprise trusted release” merely because code and repository tests pass. The strongest valid outcome is Conditional GO until the external review boundary and real release evidence are independently confirmed.
