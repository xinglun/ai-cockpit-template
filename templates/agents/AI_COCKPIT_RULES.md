This repository uses AI Cockpit as a collaborative engineering environment for AI-assisted changes. AI Change Governance is the core control mechanism inside that environment.

### Repository and Review Unit

The default unit of governed work is one Work Item, one dedicated work branch, and one pull or merge request. Do not combine unrelated Work Items on one branch or use one PR to deliver multiple independent Work Items.

For template-maintenance work, create the branch from the latest `origin/main`. For an adopter project, create the branch from the latest commit on that project's own remote default branch. The adopter remote and branch may have any names; discover them instead of assuming `origin/main`, and record the remote, default branch, and base commit in the Work Item Contract.

Installation and upgrade changes are changes in the adopter project's history. Use a published template release tag and record its source identity; do not install from a moving template work branch. After the PR is merged, delete the remote and local work branch unless a documented recovery exception applies.

### Required Workflow

1. Create or identify a version 2 Work Item Contract in `.ai/work-items/active/`.
2. Before implementation, complete `scope`, `outOfScope`, `sources`, `acceptance`, `verification`, risk, capability, and execution-decision fields.
   Treat the Contract as delegation plus description: it assigns boundaries and explains the work before changes begin.
   If the Contract contains an `intent` section, read it before implementing. When context is available, fill in at least `intent.problem` (detailed background and gap), `intent.constraints` (constraints to respect), and `intent.rationale` (why this approach). All `intent` fields are optional — do not invent content when context is not provided; leave them empty or mark them as `not provided`.
3. Read `.ai/glossary.md` and follow the Contract `guidelines`.
4. Do not change files outside the declared scope. Update the Contract first if the required scope changes.
5. Do not remove tests, snapshots, or Work Item records without documenting the reason in the Summary.
6. Update the matching AI Change Summary with changed files, verification evidence, guideline compliance, residual risks, and optional `intentAlignment` evidence when it is genuinely available.
   `unknowns` and `notCodable` are valid outputs when coding should not continue. Summary is a collaboration handoff, not only an audit artifact.
7. Run `make ai-finish TASK=<task>` and treat failures as blockers for completion or archive.
   Use checkpoints to keep long-running tasks from drifting.
8. If you need a pre-implementation readiness view, run `make ai-preflight`. Use `make generate-ai-preflight-review` when you want generation only, and `make check-ai-preflight-review` as the report validator. `make ai-start` in `MODE=code` should surface the same review before implementation begins.
   The rule is **Evidence over Self-Declaration**: readiness is derived from Contract evidence, not from agent confidence. When that review reports `needs_human_confirmation` or `not_ready`, pause and report the Preflight Review to the user before any coding continues. Advisory mode means the command can exit successfully; it does not mean the agent may silently continue.

Before editing, use Empathy, Design, Architecture, Implementation, Judgment, and Shipping as review lenses.
Do not invent missing product context. Prefer explicit "not provided" over inferred explanations.
If the user did not provide motivation or user impact, record that plainly in `problemStatement` or `unknowns` when relevant.
Treat `executionDecision` as the judgment point: continue only when scope, acceptance, verification, and unresolved unknowns support implementation.

### Safety Rules

- Never revert user changes unless the user explicitly requests it.
- Never store secrets, credentials, API keys, or machine-specific paths in governance templates.
- Do not hand-edit `.ai/cockpit/current_status.md`; generate it through the provided Make targets.
- Repository approval fields are workflow records, not trusted identity proof. Use protected platform review for trusted approval.
- AI Cockpit checks detect policy violations and block workflow completion; they do not prevent a process with filesystem access from writing files.

### Finish Criteria

Before reporting a Work Item ready for review, run every required check declared in its Contract, including scope, guards, checkpoint, agent risk, backtrack, coverage, guidelines, Summary, status, and configured project quality checks.
