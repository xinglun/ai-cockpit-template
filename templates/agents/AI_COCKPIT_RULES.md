This repository uses AI Cockpit as a collaborative engineering environment for AI-assisted changes. AI Change Governance is the core control mechanism inside that environment.

### Required Workflow

1. Create or identify a version 2 Work Item Contract in `.ai/work-items/active/`.
2. Before implementation, complete `scope`, `outOfScope`, `sources`, `acceptance`, `verification`, risk, capability, and execution-decision fields.
   Treat the Contract as delegation plus description: it assigns boundaries and explains the work before changes begin.
3. Read `.ai/glossary.md` and follow the Contract `guidelines`.
4. Do not change files outside the declared scope. Update the Contract first if the required scope changes.
5. Do not remove tests, snapshots, or Work Item records without documenting the reason in the Summary.
6. Update the matching AI Change Summary with changed files, verification evidence, guideline compliance, and residual risks.
   `unknowns` and `notCodable` are valid outputs when coding should not continue. Summary is a collaboration handoff, not only an audit artifact.
7. Run `make ai-finish TASK=<task>` and treat failures as blockers for completion or archive.
   Use checkpoints to keep long-running tasks from drifting.

### Safety Rules

- Never revert user changes unless the user explicitly requests it.
- Never store secrets, credentials, API keys, or machine-specific paths in governance templates.
- Do not hand-edit `.ai/cockpit/current_status.md`; generate it through the provided Make targets.
- Repository approval fields are workflow records, not trusted identity proof. Use protected platform review for trusted approval.
- AI Cockpit checks detect policy violations and block workflow completion; they do not prevent a process with filesystem access from writing files.

### Finish Criteria

Before reporting a Work Item ready for review, run every required check declared in its Contract, including scope, guards, checkpoint, agent risk, backtrack, coverage, guidelines, Summary, status, and configured project quality checks.
