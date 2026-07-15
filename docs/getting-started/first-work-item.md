---
author: Ray
title: "First Work Item"
description: First governed task walkthrough after AI Cockpit adoption.
keywords:
  - ai-cockpit
  - first-work-item
  - adoption
  - verification
---

# First Work Item

Use this page after installation and validation succeed. Complete the [Adopter Configuration](adopter-configuration.md) checklist before treating the repository as production-ready, then use this page for the first governed task from start to finish.

## Start a Governed Task
Each governed task uses one Work Item, one dedicated branch, and one pull or merge request. In this template repository, start from the latest `origin/main`. In an adopter project, start from the latest commit on that project's discovered remote default branch; do not assume the remote is `origin` or the branch is `main`. Record the chosen remote, branch, and base commit in the Contract.

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

`ai-start` requires the target to be a Git repository with at least one commit so `baseCommit` can identify a trustworthy diff baseline. For a new repository, create and commit its initial files before running this command. The installer prints a warning when this prerequisite is not met.

When you run `make ai-start TASK=<task> TITLE="..." MODE=code`, the command shows a Preflight Review before implementation begins. That review is advisory by default, but if it returns `needs_human_confirmation` or `not_ready`, the agent workflow must pause and report the review to the user before coding continues.

Edit the generated Contract:

```text
.ai/work-items/active/example_change.contract.json
```

Before changing project files, replace the starter placeholders and confirm this minimum checklist:

- `scope` contains every file or path pattern the task may change, and `outOfScope` states explicit boundaries.
- `sources`, `acceptance`, and `verification` describe the evidence, done conditions, and registered checks.
- `unknowns` is empty, `notCodable` is `false`, and `executionDecision.status` is `continue`.
- `agentCapability.canImplement` and `agentCapability.canVerify` are `true`; human decisions remain explicit.
- Run `make ai-checkpoint STAGE=before_edit` before implementation.

When the task is long-running, record a `before_finish` checkpoint in the Summary before running the finish flow.

Update the Summary before finishing:

```text
.ai/work-items/active/example_change.summary.json
```

Run the finish flow:

```sh
make ai-finish TASK=example_change
```

`ai-finish` runs the registered checks, updates the Summary with execution evidence, regenerates status, and archives the Contract/Summary pair. A successful walkthrough ends with no files under `.ai/work-items/active/`, an archive pair under `.ai/work-items/archive/<year>/`, and `make check-ai-status-consistency` passing. After the PR is merged, remove the corresponding remote and local work branch. Installation and upgrade tasks follow the same rule, but their source is a published template release tag recorded in the adopter project's Work Item.
