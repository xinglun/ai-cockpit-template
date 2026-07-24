---
author: Ray
title: "Interactive Installation and Calibration Wizard Implementation Plan"
description: Serial execution plan for the human-centered installation and calibration wizard feature.
keywords:
  - interactive-wizard
  - installation
  - calibration
  - work-item-lifecycle
---

# Interactive Installation and Calibration Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Every task is a separate Work Item and must complete its PR and lifecycle closure before the next task starts.

**Goal:** Add a human-centered, multilingual Installation Wizard and Calibration Wizard while preserving the existing deterministic installer, `CalibrationSession`, governance gates, and human control points.

**Architecture:** Keep core logic authoritative and make the new UI an adapter. Installation UI will consume read-only detection and installation-plan data, then call the existing transactional `Installer`; calibration UI will consume Project Doctor, Proposal, persisted `CalibrationSession`, self-check, simulation, confirmation, and atomic activation logic. New Adoption remains a bootstrap exception: no pre-existing Work Item is required, and the installer creates the first adoption Work Item only after installation.

**Tech Stack:** Python 3.10+ standard library, POSIX shell, GNU Make, existing installer/calibration scripts, JSON message resources, pytest/project quality and AI Cockpit checks.

## Global Constraints

- Preserve existing deterministic CLI installer and Calibration CLI behavior.
- New Adoption must be read-only before confirmation, must not call `make ai-start` before installation, and must not auto-commit, push, open/merge PRs, or activate governance without human confirmation.
- Upgrade must remain distinct from New Adoption and must protect project-owned files and conflict reports.
- Reuse existing Installer, Project Doctor, Proposal Generator, `CalibrationSession`, self-checks, simulation, and atomic Candidate Activation; do not create duplicate state machines or transaction logic.
- Support `ja`, `en`, and `zh-CN`; normalize `ja/ja-JP`, `en/en-US/en-GB`, and `zh/zh-CN/zh-Hans`; resolve language as `--language`, `AI_COCKPIT_LANGUAGE`, system locale, then `ja`.
- Use subprocess argument lists, never `shell=True` with user input; validate repository path, remote, branch, stack, language, and session ID.
- Dangerous actions default to `N`; show facts, recommendations, unknowns, blocking errors, examples, impact, checklist, expected result, and stop conditions.
- No planned Work Item may start until its predecessor's PR is merged, archive is complete, `make ai-close-work-item` succeeds, local and remote task branches are deleted, the default branch is synchronized, and the worktree is clean.
- The user has authorized serial execution of the full plan. Each Work Item still requires its own Contract, branch, checks, PR, merge, `ai-close-work-item`, and branch cleanup before the next begins.

## Work Item Summary

The requested feature is decomposed into the following serial Work Items. The issue-recording Work Item is first so every later Work Item has a documented place for problems and resolutions. The AI Cockpit verification-flow refactor follows it so installation and calibration implementation proceeds on the lighter, three-stage governance model. The final item is intentionally the plan-document cleanup item requested by the user.

| Order | Work Item | Deliverable | Depends on |
| --- | --- | --- | --- |
| 0 | `interactive-installation-calibration-wizard-plan` | This execution plan and its governance evidence | Latest `origin/main`; current turn authorization |
| 1 | `interactive-wizard-work-item-issue-log` | Structured issue log, per-Work-Item problem records, resolutions, residual risks, and final issue overview | Work Item 0 closure |
| 2 | `lightweight-verification-soft-gates` | Three-layer Task/PR/Release verification, unified context, impact classification, checker registry/deduplication, structured verification evidence, trend-based complexity, and legacy repayment freeze | Work Item 1 closure |
| 3 | `wizard-core-detection-plan` | Reusable read-only facts and Installation Plan model | Work Item 2 closure |
| 4 | `wizard-io-and-localization` | TTY-safe input/output, help/back/pause/quit, color/accessibility, three-language resources and parity checks | Work Item 3 closure |
| 5 | `interactive-installation-wizard` | Eight-step Installation Wizard for Target Repository, Readiness, Mode, Stack, Options, Branch, Review, Install/Result | Work Item 4 closure |
| 6 | `interactive-installation-entrypoint-compatibility` | `install.sh` routing: TTY/no-args, `--interactive`, explicit legacy CLI, non-TTY fail-closed | Work Item 5 closure |
| 7 | `interactive-calibration-wizard` | Calibration Wizard adapter over Doctor, Proposal, persisted Session, ten stages, self-check, simulation, review, confirmations, activation | Work Item 6 closure |
| 8 | `wizard-recovery-and-blocking-ux` | Stale revalidation, blocking Unknown, N/A reasons, recovery, activation-failure preservation, human handoff | Work Item 7 closure |
| 9 | `wizard-tests-and-fixtures` | Unit, integration, snapshot, TTY/non-TTY, multilingual, mobile-stack, rollback, stale, and activation-failure coverage | Work Item 8 closure |
| 10 | `wizard-documentation-and-truth-evidence` | README/guides/reference/checklists/examples, Capability Truth Matrix, troubleshooting, roadmap/version history, release evidence | Work Item 9 closure |
| 11 | `wizard-final-verification-and-user-report` | Full quality/governance/release verification, final issue overview, and explicit Known Gaps report | Work Item 10 closure |
| 12 | `clean-interactive-wizard-execution-plan-documents` | Remove or archive superseded execution-plan documents, update plan index/evidence, verify no stale plan remains | Work Item 11 closure |

## Mandatory Lifecycle for Every Work Item

The following procedure is part of every Work Item, including Work Item 0 and Work Item 12. It is not optional and must be repeated serially:

1. Confirm the predecessor closure evidence. Fetch the repository's latest remote default branch, discover the remote/default branch rather than assuming it for adopter repositories, record `baseRemote`, `baseBranch`, and `baseCommit`, and create a dedicated `codex/<work-item>` branch directly from that base.
2. Run `make ai-start TASK=<task> TITLE="..." MODE=code`, complete the v2 Contract (`intent`, `scope`, `outOfScope`, `sources`, `unknowns`, `acceptance`, `scenarioCoverage`, `verification`, `budgetImpact`, `agentCapability`, and `executionDecision`), then run `make ai-preflight`, `make check-ai-serial-order`, and `make check-ai-budget-impact`. A `needs_human_confirmation`, `not_ready`, stale-base, unknown, or budget failure stops the Work Item.
3. Implement only the declared scope using TDD where behavior changes: write focused failing tests, implement the smallest change, run focused tests, and preserve user changes.
4. Update the AI Change Summary with changed files, verification results, guideline compliance, checkpoint evidence, review readiness, known gaps, residual risks, and any user correction solidification.
5. Run the Contract's required AI and project checks, including `check-ai-contract`, `check-ai-scope`, `check-ai-guards`, `ai-checkpoint` at `before_finish`, `check-ai-agent-risk`, `check-ai-review-policy`, `check-ai-backtrack`, `check-ai-coverage-guard`, `check-ai-guidelines`, `check-ai-change-summary`, `generate-cockpit-status`, `check-ai-status`, and `check-ai-status-consistency`, plus the Work Item's quality checks.
6. Run `make ai-finish TASK=<task>` only after checks pass and human review authorization for archival is present. Confirm the archive is complete and run `make check-ai-pr AI_BASE_COMMIT=<base>` before opening a PR. The PR must contain exactly one Work Item and its evidence.
7. Push the dedicated branch, open the PR, wait for required review/CI checks, address review, and merge the PR. Do not merge locally into the default branch and do not delete the task branch before closure.
8. After merge, run `make ai-close-work-item TASK=<task>`. It must verify archived Contract/Summary/Status, one-to-one branch/PR ownership, fast-forward-only base synchronization, clean worktree, local and remote task-branch deletion, and local-base equality with the remote base. If it fails, stop and repair only within the current Work Item.
9. Confirm the default branch is synchronized with its remote, the worktree is clean, the task branch is gone locally and remotely, and closure reports `ready for next Work Item`. Only then begin the next numbered Work Item.

## Detailed Work Items

### Work Item 0: `interactive-installation-calibration-wizard-plan`

**Files:**

- Create: `docs/superpowers/plans/2026-07-25-interactive-installation-calibration-wizard.md`
- Modify: `.ai/work-items/active/interactive-installation-calibration-wizard-plan.contract.json`
- Modify: `.ai/work-items/active/interactive-installation-calibration-wizard-plan.summary.json`
- Generate: `.ai/cockpit/current_status.md`

**Purpose:** Capture the received specification, confirm the intended boundaries, decompose implementation into serial review units, and document the full PR/cleanup lifecycle.

**Acceptance:**

- The plan covers Bootstrap Adoption, New Adoption vs Upgrade, both wizard entrypoints, core/UI separation, standard-library constraint, subprocess safety, three languages, all eight installation steps, ten calibration stages, blocking/unknown/recovery behavior, tests, docs, truth matrix, compatibility, release evidence, and the final self-check report.
- The table ends with `clean-interactive-wizard-execution-plan-documents`.
- The plan records that the user authorized serial execution of every Work Item, while each Work Item retains its own full PR and lifecycle-closure boundary.
- This Work Item itself completes the full lifecycle in the Mandatory Lifecycle section, then stops for user review.

**Verification:** Contract/preflight, all repository AI checks declared by the Contract, markdown/link/plan checks if present, clean diff ownership, PR ownership, merged-PR closure, and clean base synchronization.

### Work Item 1: `interactive-wizard-work-item-issue-log`

**Files:**

- Create: `scripts/ai_verify.py`, `scripts/ai_verification_context.py`, `scripts/ai_impact_classifier.py`, `scripts/ai_check_registry.py`
- Create: `.ai/policies/complexity_trend.yaml`, `.ai/policies/verification_impact.yaml`
- Create: `docs/architecture/lightweight-verification-and-soft-gates.md`, `docs/maintainers/adding-or-classifying-a-check.md`, and synchronized Japanese/English/Chinese user guidance
- Modify: `Makefile`, existing checker registration/orchestration, complexity policy readers, and only the tests required by the Contract
- Preserve: all existing `.ai/work-items/archive/**` history and historical `repaymentRecords`

**Purpose:** Establish a durable, structured record for every problem encountered during the serial plan, without silently treating warnings, blocked states, external failures, scope corrections, or verification gaps as resolved.

**Implementation:** Define one record per issue with Work Item, stage, timestamp, severity (`informational`, `warning`, `needs_human_confirmation`, or `blocked`), observed evidence, impact, owner, immediate containment, resolution or explicit unresolved state, verification reference, and whether the issue affects the final completion claim. Every later Work Item must append or reference its issue records during Summary and final closure; historical records must not be rewritten. The final verification Work Item must produce a complete issue overview as a document for the user to review after the plan completes.

Move normal complexity growth, archive count, checker count, documentation drift, and duration changes to trend warnings or human confirmation. Keep dependency cycles, Secret exposure, Evidence/Commit mismatch or tampering, unauthorized files, Trust Boundary removal, Fail Closed to Fail Open changes, missing Human Confirmation, validator failure, and Release Identity failures as hard gates. Freeze historical repayment records without editing them and stop creating per-Task line/archive repayment entries. Treat `current_status.json` and `.md` as derived views generated from `verification.json`, not machine facts.

**Verification:** Validate the issue schema, append-only behavior, Work Item and commit binding, redaction of secrets, one-to-one links from issue records to Summary/Verification evidence, and a final report that distinguishes resolved issues from accepted residual risks and blockers. Demonstrate that an unresolved Hard Gate or missing evidence cannot be reported as Green.

**Lifecycle boundary:** This Work Item creates the issue-recording mechanism only. It must complete its own PR and closure before Work Item 2, the verification optimization, starts.

### Work Item 2: `lightweight-verification-soft-gates`

**Files:**

- Create: `docs/superpowers/plans/2026-07-25-interactive-wizard-work-item-issue-log.md`
- Create: the Contract-scoped structured issue-log evidence for this Work Item
- Modify: the execution-plan document only where the issue-log schema, update cadence, ownership, and final reporting gate must be referenced

**Purpose:** Replace the user-visible verification surface with Task, PR, and Release while preserving one Task = one Branch = one PR, Trust Boundaries, Human Confirmation, Evidence/Commit binding, irreversible-operation protection, and strict Release proof.

**Implementation:** Build one immutable `VerificationContext` that reads Git diff, Contract, Summary, project profile, impact policy, and complexity policy once. Classify changed files into docs, project code, tests, governance, trust, dependency, installer, lifecycle, release, workflow, or unknown. Register each Checker once per verification run and emit structured `CheckResult` records with `hard`, `soft`, or `informational` gate type. Record every stage-inapplicable check as `skipped` with a reason code; the Agent may not invent skip decisions. Keep Task checks focused on changed files and affected tests, PR checks on core project health and critical trust checks, and Release checks on full strict proof including supply chain, installer lifecycle, compatibility, identity, assets, and distribution.

Move normal complexity growth, archive count, checker count, documentation drift, and duration changes to trend warnings or human confirmation. Keep dependency cycles, Secret exposure, Evidence/Commit mismatch or tampering, unauthorized files, Trust Boundary removal, Fail Closed to Fail Open changes, missing Human Confirmation, validator failure, and Release Identity failures as hard gates. Freeze historical repayment records without editing them and stop creating per-Task line/archive repayment entries. Treat `current_status.json` and `.md` as derived views generated from `verification.json`, not machine facts.

**Verification:** Test hard/soft/informational decisions, threshold escalation, immutable context and single-read behavior, impact classification including unknown files, checker deduplication, explicit skipped-check reasons, legacy/unified/compare modes, Task/PR/Release command compatibility, trend behavior with insufficient samples, historical repayment preservation, Release strictness, and regression protection for every retained hard gate. Measure subprocess, checker, Git, parse, and Release-check counts for docs-only, project-code, governance, installer, and release changes. The Work Item must demonstrate that no dangerous legacy hard failure becomes Green without `needs_human_confirmation`.

**Lifecycle boundary:** This Work Item changes verification/governance behavior only. It must complete its own PR and closure before Work Item 3, the installation improvement plan, starts.

### Work Item 3: `wizard-core-detection-plan`

**Files to inspect/change:** `scripts/ai_install_facts.py`, `scripts/ai_installer_detection.py`, `scripts/ai_installer_repository.py`, `scripts/ai_installer_bootstrap.py`, `scripts/install_ai_cockpit.py`, related installer tests.

**Implementation:** Extract or expose typed read-only detection for Git, remote/default branch, clean worktree, tracked hygiene files, symlink risk, Python/Git/Make/curl/POSIX toolchain, runtime presence, stack signals, and New Adoption/Upgrade readiness. Add an Installation Plan data structure that contains facts, recommendation, impact, examples, write boundary, expected result, stop condition, and checklist. Keep transaction, branch creation, rollback, and Work Item creation in existing installer code.

**Verification:** Unit tests prove detection is read-only and plan serialization is deterministic; tests prove New Adoption does not require an existing Work Item and that Upgrade detects active Work Items/conflicts.

### Work Item 4: `wizard-io-and-localization`

**Files to create/modify:** `scripts/ai_wizard_io.py`, `scripts/wizard_messages/ja.json`, `scripts/wizard_messages/en.json`, `scripts/wizard_messages/zh-CN.json`, `scripts/ai_wizard_messages.py`, `tests/test_wizard_io.py`, `tests/test_wizard_messages.py`.

**Implementation:** Provide argument-list-safe input primitives for Y/N, selection, text input, Back, Pause, Quit, Help, EOF, Ctrl+C, TTY detection, non-color output, and accessible status symbols. Normalize language aliases and enforce exact key/placeholder parity at startup and in tests. Keep Wizard language independent from detected project documentation language. Do not silently fall back to another language for user-visible content.

**Verification:** Unit tests cover all aliases, locale precedence, default `ja`, non-TTY no-input behavior, EOF/Ctrl+C, dangerous default N, and three-language key/placeholder equality.

### Work Item 5: `interactive-installation-wizard`

**Files to create/modify:** `scripts/ai_install_wizard.py`, `scripts/ai_install_plan.py`, installer integration tests and snapshots.

**Implementation:** Implement the eight fixed steps: Target Repository; Repository Readiness; Installation Mode; Project Stack; Installation Options; Adoption Branch; Installation Plan Review; Installation/Result. Each step renders Purpose, why, facts, suggested value, option impact, concrete example, write status, expected result, stop condition, and checklist. Support New Adoption, Upgrade, Dry Run, iOS Swift Package/Xcode/Workspace/CocoaPods, Android modules/flavors/variants/JDK/test signals, Generic, and multi-stack repositories. Before final confirmation, show the complete plan and explicit no-commit/no-push/no-PR/no-merge behavior. Before confirmation, do not write to the target repository; transient recovery may use only a system temp directory.

**Verification:** Scripted wizard tests assert no target writes before confirmation, correct installer reuse after confirmation, branch/remote facts are real, conflict files are protected, and dry run is strictly read-only.

### Work Item 6: `interactive-installation-entrypoint-compatibility`

**Files to modify:** `install.sh`, `scripts/install_ai_cockpit.py` only where routing is required, shell/install tests.

**Implementation:** Route no-argument TTY execution to the wizard, `--interactive` to the wizard, explicit installer options to the existing deterministic path, and no-argument non-TTY execution to fail closed without waiting. Preserve all existing CLI flags and output semantics. Do not add auto-commit, push, PR, or merge behavior.

**Verification:** `bash -n install.sh`, ShellCheck, legacy CLI regression tests, TTY and non-TTY integration tests, and explicit dry-run tests.

### Work Item 7: `interactive-calibration-wizard`

**Files to create/modify:** `scripts/ai_calibration_wizard.py`, `Makefile`, calibration tests.

**Implementation:** Add the future calibration-wizard Make target and direct Python entrypoint. Reuse Project Doctor, Proposal, `CalibrationSession`, `target/ai_project_doctor_report.json`, `.ai/project_profile.proposed.yaml`, `.ai/calibration/session.json`, and `.ai/calibration/active.json`. Render the fixed ten stages with Y/N/Input/Unknown/N/A (N/A requires a reason), stage self-check, full self-check, governance simulation, Back, Pause/Resume, stale detection/revalidation, final review, separate Reviewer and Owner confirmations, and atomic Candidate Activation. Never duplicate session state transitions or activation logic.

**Verification:** Calibration tests prove persisted resume, fixed stage order, Back behavior, self-check/simulation reuse, separate confirmations, and activation preserves the original Active Configuration on failure.

### Work Item 8: `wizard-recovery-and-blocking-ux`

**Files to modify:** wizard UI/core modules, message resources, tests, troubleshooting docs only if required by the Contract.

**Implementation:** Make Unknown explicit; block confirmation on Blocking Unknown; require reasons for N/A; show stale state and require revalidation; provide Pause/Resume recovery and safe Quit; ensure partial failures report completed/incomplete items and never claim activation. Validate all user-controlled identifiers and subprocess arguments. Ensure secret values are never displayed or persisted.

**Verification:** Tests cover dirty worktree, missing remote/default branch, stale session, invalid input, EOF/Ctrl+C, interrupted installation rollback, blocking unknown, and activation failure with original active configuration retained.

### Work Item 9: `wizard-tests-and-fixtures`

**Files to create/modify:** `tests/test_wizard_*.py`, integration fixture harness, snapshot fixtures, mobile project fixtures.

**Implementation:** Add the requested scenarios: iOS Swift Package dry run; iOS Xcode Workspace New Adoption; Android New Adoption; mobile monorepo; dirty worktree; existing-runtime Upgrade; Calibration resume; stale session; activation failure. Add snapshots for all three languages and representative facts/plan/checklist/result output. Cover iOS Package/Project/Workspace/CocoaPods, Android application/multi-module/flavor/variant/JDK/unit/instrumented tests, generic mixed monorepo, and Upgrade.

**Verification:** Run focused tests first, then the complete unit/integration/snapshot suite; record test count, Python versions, and any unavailable external checks in the Summary rather than overstating coverage.

### Work Item 10: `wizard-documentation-and-truth-evidence`

**Files to modify:** `README.md`, `README.ja.md`, installation guides, Calibration Session reference, Capability Truth Matrix, documentation architecture, adoption checklist, troubleshooting, roadmap/version history, release evidence files as required.

**Implementation:** Document both entrypoints, bootstrap boundary, step-by-step examples, New Adoption vs Upgrade, dry run, mobile examples, calibration stages and confirmations, blocking/recovery behavior, operator checklist, troubleshooting, capability claims, and the distinction between Wizard language and project language. Update release identity, installer digest, archive SHA256, SBOM, and provenance only through their prescribed generators/checks.

**Verification:** Documentation metadata/link checks, truth-matrix validation, `make quality`, `make check-ai`, release evidence checks, and review for no unsupported capability claims.

### Work Item 11: `wizard-final-verification-and-user-report`

**Files:** Only files required by evidence corrections; create the final completion report in the Work Item Summary or the repository's prescribed evidence location.

**Implementation:** Run the full project and governance verification matrix. Report new/modified files, entrypoints, core reuse points, absence of duplicate logic, bootstrap guarantees, dry-run read-only guarantee, language/key/placeholder parity, iOS/Android/generic coverage, safety properties, test count/results/versions, quality/governance/release verification, documentation coverage, and every Known Gap. Do not use “basically complete”; unresolved items remain explicit and block a ready claim when required.

**Verification:** All required checks pass or are explicitly recorded as not run with a reason; required CI checks are green before merge; the PR contains only this Work Item.

### Work Item 12: `clean-interactive-wizard-execution-plan-documents`

**Files:** Superseded plan documents identified by read-only inventory; `docs/superpowers/plans/README.md` or index; Work Item evidence for the cleanup.

**Precondition:** Work Items 1–11 have each completed PR merge, archive, `ai-close-work-item`, local/remote task-branch cleanup, default-base synchronization, and clean-worktree verification. This item is never started early.

**Implementation:** Inventory plan/spec documents related to the Interactive Installation and Calibration Wizard, identify the canonical completed plan and any superseded duplicates, then remove or archive only the explicitly approved obsolete documents. Update the plan index and references so no stale execution plan remains. Do not delete Work Item evidence or active/archived governance records without a documented reason and guard approval.

**Verification:** Read-only before/after inventory, link/reference checks, scope and ownership checks, clean diff, and the complete Mandatory Lifecycle. The final closure report must state exactly what was removed or retained and why.

## Stop and Human Confirmation Gates

The following are already authorized: update and validate the execution plan so that the issue-record mechanism is Work Item 1, the lightweight verification and soft-gate refactor is Work Item 2, and the installation improvement starts at Work Item 3. The user has also authorized serial execution of every Work Item, with full PR and closure lifecycle, followed by a final issue overview document for user review.

The following are not authorized without the applicable Work Item Contract and its serial predecessor closure: scope expansion beyond the current Work Item, unrecorded Hard Gate bypasses, deletion or rewriting of historical Archive/Evidence, or claiming the entire plan complete before the final issue overview document is produced. Each authorized Work Item still requires its own Contract, branch, PR, merge, closure, and cleanup before the next starts.

Any preflight report of `needs_human_confirmation` or `not_ready`, any unknown, stale base, scope conflict, missing required check, review disagreement, or release-evidence mismatch pauses the current Work Item and is reported with its evidence path. No later Work Item may be used to bypass that gate.

## Plan Self-Review

- Spec coverage: mapped issue recording to Work Item 1; mapped the verification-flow refactor sections 1–30 to Work Item 2; mapped final reporting to Work Item 11; mapped the installation/calibration specification sections 4–8 to Work Items 3–4; sections 9–18 to Work Items 5–6; sections 19–29 to Work Items 7–8; sections 30–33 to Work Items 5, 7, 9, and 10; sections 34–41 to Work Items 4–9; sections 42–46 to Work Item 10; sections 47–50 to Work Items 8–11; and the final cleanup requirement to Work Item 12.
- Placeholder scan: no `TBD`, `TODO`, or unspecified “add appropriate handling” step is used as an acceptance criterion; each Work Item names its boundary and verification.
- Boundary consistency: the verification refactor owns orchestration and evidence only; Installation UI calls the existing installer; Calibration UI calls the existing `CalibrationSession` and activation logic; future Work Items remain serial and one-to-one with PRs.
- User review condition: all Work Items must close serially; Work Item 11 must produce the complete issue overview document, and the user reviews that document after Work Item 12 closes the plan-document cleanup. Completion does not require retaining `needs_human_confirmation` as the final plan state.
