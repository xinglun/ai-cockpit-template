# ai-cockpit-template

Language-agnostic AI governance template. Works with Rust, Flutter, TypeScript, Python, and other codebases by customizing Makefile checks and scope rules.

This template gives Codex, Gemini, Antigravity, and other coding agents an engineering-grade workflow for bounded code changes, verification, and audit records.

## What It Provides

- Work Item Contract: the task boundary before an AI agent changes files.
- Scope Guard: blocks changes outside the declared scope.
- Backtrack Guard: reports undeclared removal of tests, snapshots, or audit records.
- Coverage Guard: reports production changes without matching test changes.
- Change Summary: records what changed, what was verified, and what risk remains.
- Cockpit Status: a generated one-screen view of the current AI task state.
- Finish Flow: validates checks and archives the Work Item only after the workflow passes.

## Repository Layout

```text
.ai/
  cockpit/
    README.md
    checks.yaml
    current_status.md
  guards/
    file_boundary.yaml
    file_ownership.yaml
    backtrack_policy.yaml
    coverage_policy.yaml
    scope_policy.yaml
    summary_policy.yaml
    cockpit_status_policy.yaml
  work-items/
    _templates/
    active/
    archive/
scripts/
  ai_start.py
  ai_finish.py
  ai_check_work_item.py
  ai_check_scope.py
  ai_check_guards.py
  ai_check_backtrack.py
  ai_check_coverage_guard.py
  ai_check_summary.py
  ai_generate_status.py
  ai_check_status.py
  ai_archive_work_item.py
examples/
  rust/
  flutter/
  typescript/
```

## Quick Start

Use this repository directly as a GitHub template for new projects, or install AI Cockpit into an existing repository.

### Install Into An Existing Repository

From a local clone of this template:

```sh
/path/to/ai-cockpit-template/install.sh --stack rust
```

For a remote GitHub repository, set the template repo and pipe the installer:

```sh
AI_COCKPIT_TEMPLATE_REPO=OWNER/ai-cockpit-template \
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/OWNER/ai-cockpit-template/main/install.sh)" -- --stack rust
```

Safer two-step remote install:

```sh
curl -fsSL https://raw.githubusercontent.com/OWNER/ai-cockpit-template/main/install.sh -o install-ai-cockpit.sh
AI_COCKPIT_TEMPLATE_REPO=OWNER/ai-cockpit-template sh install-ai-cockpit.sh --stack rust
```

Supported stack presets:

```text
generic, rust, flutter, typescript, python
```

Installer options:

```text
--dry-run          Show actions without writing files.
--force            Overwrite existing AI Cockpit files.
--with-examples    Copy examples/ into the target repository.
--update-makefile  Append "include Makefile.ai" to the target Makefile.
```

By default, the installer is conservative:

- It writes `Makefile.ai` and `Makefile.ai.stack` instead of modifying an existing Makefile.
- It appends AI Cockpit sections to existing `AGENTS.md` and `GEMINI.md`.
- It skips existing files unless `--force` is provided.

After install, add this line to your project Makefile unless you used `--update-makefile`:

```make
include Makefile.ai
```

### Start A Work Item

Create a Work Item:

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

Edit the generated Contract:

```text
.ai/work-items/active/example_change.contract.json
```

Make the actual code or documentation changes inside the declared `scope`.

Update the Summary:

```text
.ai/work-items/active/example_change.summary.json
```

Run the finish flow:

```sh
make ai-finish TASK=example_change
```

The finish flow runs AI checks, generates `.ai/cockpit/current_status.md`, checks the status, runs project quality checks, then archives the Contract and Summary when everything passes.

## Customizing Project Checks

The template keeps project-specific commands in the Makefile:

```make
project-format-check:
	cargo fmt --all -- --check

project-test:
	cargo test

project-lint:
	cargo clippy --all-targets -- -D warnings
```

For Flutter:

```make
project-format-check:
	dart format --set-exit-if-changed .

project-test:
	flutter test

project-lint:
	flutter analyze
```

For TypeScript:

```make
project-format-check:
	npm run format:check

project-test:
	npm test

project-lint:
	npm run lint
```

You can also update `.ai/cockpit/checks.yaml` so agents know which checks to choose for each task.

## Guard Configuration

- `.ai/guards/file_ownership.yaml` controls restricted and forbidden AI writes.
- `.ai/guards/file_boundary.yaml` blocks generated and runtime artifacts from entering code diffs.
- `.ai/guards/coverage_policy.yaml` defines production and test path patterns.
- `.ai/guards/scope_policy.yaml` defines paths that are always allowed and optional dependency scope rules.

The guard YAML parser intentionally supports a small subset of YAML so the scripts can run with Python's standard library only.

## Suggested Repository Topics

`ai-agents`, `codex`, `gemini`, `agentic-coding`, `developer-tools`, `governance`, `template`, `automation`, `ci`

## Template Policy

Do not add business logic, personal paths, real API keys, GitHub secrets, or organization-specific runtime configuration to this repository. Keep examples generic and move real project policy into the adopting repository.
