---
author: Ray
title: "AI Cockpit"
description: AI Cockpit workspace overview and workflow guide.
keywords:
  - ai-cockpit
  - work-item-contract
  - scope-guard
  - change-summary
  - cockpit-status
---

# AI Cockpit

[日本語](README.ja.md)

AI Cockpit is a Repository Governance Layer for AI-assisted development. It provides governance contracts, verification gates, and audit trails for AI agents (Codex, Gemini, Claude, Cursor, Antigravity, etc.).

AI Cockpit is intentionally language-agnostic. It provides AI Change Governance through explicit scope, delegated checks, review evidence, and auditable task records, while the Makefile delegates product-specific checks to commands that each repository can customize.

## The Governance Loop

```text
Intent → Contract → Implementation → Verification → Summary (Intent Alignment)
```

| Phase | Purpose |
| --- | --- |
| **Intent** | Why does this work exist? (problem, constraints, rationale; optional and can be left as not provided) |
| **Contract** | What should change? (scope, acceptance, verification) |
| **Implementation** | What actually changed? |
| **Verification** | Does it meet requirements? |
| **Summary** | Did we achieve the intended goal? |

## Governance Compression

V2.5 adds a second layer after Repository Truth is established:

```text
Summary (Repository Truth) → Cockpit (Governance Compression) → Human Decision
```

Cockpit does not duplicate Summary. It compresses contract, summary, and verification evidence into decision-oriented status for reviewers and maintainers.

`current_status.md` now surfaces:

- `Recommendation`
- `Governance Signals`
- `Evidence`
- `Decision Drivers`

These fields should remain explainable and conservative. Missing evidence should not be rewritten as a positive outcome.

V2.6 adds a generic `Scenario Coverage` signal for medium/high risk Work Items. It distinguishes `complete`, `incomplete`, `not_required`, and `unknown` without hard-coding release/auth/installer scenario libraries into Core. The policy source lives in `.ai/guards/scenario_coverage_policy.yaml`; scenario content stays in the Work Item, while Cockpit only compresses the evidence into a reviewer-facing signal.

V2.6.5 adds Preflight Review. It follows the principle of **Evidence over Self-Declaration**: implementation readiness is derived from Contract evidence, not from agent confidence. `make ai-start TASK=<task> TITLE="..." MODE=code` and `make ai-preflight` surface that review before implementation begins. The template default is the enforced profile: `needs_human_confirmation`, `human_decision_recorded`, and `not_ready` stop the governance path. A repository that needs compatibility behavior may explicitly use an advisory policy with `profile: advisory`, `gateEnabled: false`, and `blockedStatuses: []`; advisory mode is not the formal Trust Layer proof.

When `.ai/guards/preflight_review_policy.yaml` uses the enforced profile, the pause is a fail-closed Human Decision Gate. Decision Evidence is stored in the active Summary under `decisionEvidence` with `decisionId`, `decision`, `workItemId`, `contractHash`, `preflightHash`, `recordedAt`, and `recordedBy`. Record a selected option from the current request with:

```text
$(PYTHON) scripts/ai_preflight_review.py --contract .ai/work-items/active/<task>.contract.json --record-decision --decision A --recorded-by <person>
```

The evidence is accepted only when its Work Item, Contract Hash, Decision ID, and Preflight Hash match the current report. After recording it, rerun Preflight; `human_decision_recorded` is still paused, and only a newly recomputed `ready` report permits implementation or finish. Missing, stale, or mismatched evidence causes the Gate to fail closed. Advisory compatibility is opt-in and must be visible in the selected policy.

Complexity policy changes follow the same boundary: a proposal remains inactive until its policy state is explicitly `confirmed` with review evidence. Every hard budget increase must include a repayment record; a missing or stale record is a blocking signal, not an allow result. `archiveGrowth` is observational when the policy declares `enforcement.archiveGrowth: warning`: the configured threshold (currently 200) is reported as a warning and does not block archive, PR, or release flow. Archive evidence integrity remains fail-closed: duplicate archive sequences, missing pairs, digest mismatches, and inconsistent Contract/Summary records are still errors.

## Core Files

- `checks.yaml`: check catalog and project-specific command selection guidance.
- `current_status.md`: generated status view for the active Work Item.
- `.ai/guards/scenario_coverage_policy.yaml`: generic policy source that decides when scenario coverage is required.
- `.ai/work-items/active/*.contract.json`: task boundary before work starts.
- `.ai/work-items/active/*.summary.json`: change report before finish.
- `.ai/guards/*.yaml`: file ownership, boundary, scope, backtrack, and coverage rules.

## Flow

### Repository roles and review units
The default review unit is one Work Item, one dedicated work branch, and one pull or merge request. A Work Item must not be split across unrelated branches or combined with unrelated Work Items in one PR.
The branch base depends on the repository role:

- In the template repository, create maintenance branches from the latest `origin/main`.
- In an adopter project, create branches from the latest commit on that project's remote default branch. Discover the remote and branch; do not assume `origin/main`. Record `baseRemote`, `baseBranch`, and `baseCommit` in the Work Item when workflow metadata is used.
Installation and upgrade work is committed to the adopter project's repository. It consumes a published template release tag, not a moving template branch. After merge, remove the remote and local work branch unless a documented recovery exception applies.

### Lifecycle closure

Use `make ai-close-work-item TASK=<task>` after the Work Item is archived and its PR is merged. The command verifies the archived Contract/Summary/Cockpit Status, the one-to-one branch/PR mapping, fast-forward-only base synchronization, local and remote branch deletion, a clean repository, and local-base equality with the remote base. It fails closed on any error and reports `ready for next Work Item` only after every postcondition passes.

The required order is: latest remote base, dedicated Work Item branch, implementation, `ai-finish`/archive, push, PR, PR merge, then `ai-close-work-item`. Do not merge the feature branch into local `main` before the PR, and do not delete the Work Item branch before closure; otherwise local `main` can diverge from `origin/main` or the merged branch identity can be lost before ownership verification.

`ai-close-work-item` is worktree-aware. If the base branch is checked out in another worktree, it verifies that worktree is clean, fast-forwards and validates the base there, detaches the Work Item worktree, then removes the local and remote Work Item branches. Historical archive evidence is retained. The governance complexity report still records `trackedFiles`, but that metric is observational; archive integrity and current-task ownership remain hard gates.

1. Declare Intent (optional but recommended): Why does this work exist? What constraints must be respected? What's the rationale?
2. Create a Work Item with `make ai-start TASK=<task> TITLE="..." MODE=code`.
3. Edit the Contract until scope, sources, acceptance, verification, risk assessment, agent capability, and execution decision are explicit. Fill `intent.problem`, `intent.constraints`, and `intent.rationale` when context is available, or leave them empty / not provided when context is missing.
4. Implement only inside the declared scope.
5. Update the Summary with changed files, checks, risks, review readiness, boundary checks, known gaps, any destructive changes, and optional `intentAlignment` evidence when it exists.
6. Run `make ai-finish TASK=<task>`; this archives the evidence but does not close the lifecycle.
7. Push the Work Item branch, open and merge its PR, then run `make ai-close-work-item TASK=<task>`.
8. Review the generated status and confirm the closure command reports `ready for next Work Item`.

If you want the startup flow to surface readiness before implementation, run `make ai-preflight`.
That target generates the Preflight Review and then validates it. With the default enforced policy, `needs_human_confirmation`, `human_decision_recorded`, and `not_ready` fail the check; an explicit advisory policy keeps the compatibility behavior.
`make generate-ai-preflight-review` still exists if you want to generate the report without the validation step.
`make check-ai-preflight-review` validates the generated report structure and only acts as a gate when the policy enables it.

When `ai-start` or `ai-preflight` reports `needs_human_confirmation` or `not_ready`, the agent must pause and report the Preflight Review to the user before implementation continues.
Cockpit Status keeps the Preflight Review visible for reviewers, but it does not replace that pre-implementation pause.

When the status is `needs_human_confirmation`, the Preflight report also contains a `humanDecisionRequest` with what happened, why it matters, available options, the recommended option and reason, the decision question, and the resume condition. This object makes the pause actionable; it does not itself enforce a gate or record a human decision.

Explicit blockers also produce `not_ready`: `notCodable: true`; `executionDecision.status` of `block`, `defer`, or `needs_human_decision`; and a declared `agentCapability` that cannot implement, cannot verify, or requires human decision.

Intent drives Contract. Contract drives Implementation. Verification validates execution. Summary validates alignment back to Intent.
Summary becomes Repository Truth, and Cockpit compresses that truth into a human decision state.

Unknowns and `notCodable` are valid outputs, not failures. Summary is both an audit record and a collaboration handoff. Checkpoints exist to reduce drift in longer tasks, not merely to satisfy compliance.

`current_status.md` is generated. Do not hand-edit it.

Run `make ai-lifecycle-facts` to emit the deterministic, read-only lifecycle fact source as JSON. It reports bootstrap, calibration, governed development, or no-active-work-item state plus active Work Item counts. The output is an observation boundary: `readiness` and `enterpriseAssurance` remain `not_claimed`, and provider assets and external enterprise assurance remain `not_run`.

## Post-Install Onboarding

After installation, consolidate doctor, calibration, and readiness guidance into three phases:

```sh
make ai-onboard              # environment → calibration → readiness
make ai-onboard PHASE=1      # environment only
make ai-onboard PHASE=2      # calibration only
make ai-onboard PHASE=3      # readiness only
```

See [Adoption Readiness](adoption.md) for the detailed checklist.

## Lifecycle Checks

`make ai-start` runs a lifecycle preflight before creating a new skeleton. It refuses to start when active Contract/Summary files are unpaired, more than one Work Item is active, or `current_status.md` disagrees with the active/no-active state.
In `MODE=code`, it also runs `make ai-preflight` so the Preflight Review is shown before implementation begins. If that review reports `needs_human_confirmation` or `not_ready`, the agent must pause, present the review to the user, and only then continue with implementation decisions.
When the explicit Preflight Gate is enabled, `ai-start` and `ai-finish` return a failure for missing or invalid Decision Evidence and for any state that has not been freshly recomputed as `ready`.

Run `make check-ai-status-consistency` after generating or checking `current_status.md` when you need to validate the lifecycle state without finishing the Work Item.

Run `make repair-ai-status` to regenerate `current_status.md` when there is no active Work Item or exactly one active Contract/Summary pair. It does not repair unpaired files or multiple active Work Items; those require manual cleanup.

After archive, the generated state is `no_active_work_item`. It means no active Contract/Summary pair. No-active status deliberately omits the file list and persists a deterministic clean marker; transient archive-time worktree changes are not serialized. Commit the complete archived bundle first, then use `make check-ai-pr AI_BASE_COMMIT=<merge-base>` to validate the clean committed PR diff and archive ownership. `make repair-ai-status` only regenerates status for a valid zero- or one-active-pair lifecycle state; it does not repair ownership evidence.

`make check-ai-diff-ownership` is the earlier, read-only ownership preview. Without `AI_BASE_COMMIT` it evaluates the local worktree (including untracked files); with `AI_BASE_COMMIT=<merge-base>` it evaluates the PR diff using the same newly added archive pairs that `check-ai-pr` consumes. Its states are `active_owned`, `archived_owned`, `unowned`, `ambiguous`, `out_of_scope`, and `approval_required`. In PR mode the audit resolves overlapping archive claims deterministically, with the latest matching archive pair winning. Resolve every state except the two `*_owned` states before finishing; create a new Work Item for later changes rather than editing archive evidence.

`make ai-pre-merge AI_BASE_COMMIT=<merge-base>` reports four layers in order: content quality, lifecycle consistency, ownership preview, and final PR audit. A failure in any layer means commit/merge is not allowed; `check-ai-pr` remains the final authority.

## Agent Risk Controls

AI Cockpit treats prompt instructions as guidance, not enforcement. Repository safety comes from hard gates that inspect the actual Work Item and diff.

The default template maps three common agent risks to controls:

- Prompt is advice: `make check-ai-agent-risk` verifies required AI gates are present in the Contract verification list and passed in the Summary when a Summary is provided.
- Mid-task drift: `make ai-checkpoint` prints intent context (problem, constraints, rationale), scope, out-of-scope files, unknowns, acceptance, required check status, review focus, next action, and checkpoint integrity metadata.
- Unknown overclaim: Contract validation and Agent Risk Guard require unknowns or `notCodable` states to use a non-coding execution decision instead of continuing implementation.

Record checkpoint usage in Summary `checkpointEvidence` before finishing when the Contract `checkpointPolicy.requiredBeforeFinish` is true.

Keep these concepts separate:

- `unknowns`: unresolved facts or design questions.
- `scenarioCoverage`: known scenarios that are verified, unverified, or not_applicable.
- `residualRisks`: reviewer-accepted risks that remain after implementation.
- `followUps`: concrete future actions that were not resolved in the current Work Item.
- `unverifiedScenarios`: scenario names that must remain visible until they are verified.

## Review Readiness

The Contract readiness fields record whether the agent can implement and verify the task before coding starts. The Summary readiness fields record residual risks, expected review focus, boundary checks, user corrections, known gaps, and claims that were not verified.

Keep these fields language-neutral when this template is copied into another repository.

Run `make check-ai-review-policy SUMMARY=<summary.json>` to report governance-sensitive paths declared in `.ai/guards/ai_review_policy.yaml`. The check is report-only and records whether `reviewReadiness.expectedReviewFocus` is present in the Summary.

After archive, PR CI runs `make check-ai-pr AI_BASE_COMMIT=<merge-base>`. The installed distribution includes this target and validator. Every non-exempt path in the complete PR diff must be owned by exactly one changed archive pair: scoped by its Contract, not excluded by that Contract, and reported by its paired Summary.

PR evidence requires Contract version 2; version 1 is legacy-read-only and cannot be introduced as new PR evidence. Contract approval fields are self-declared records, not proof of human identity. Use protected platform review for trusted approval and run project tests independently from the governance PR check.
