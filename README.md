---
author: Ray
description: Language-agnostic AI governance template for Codex, Gemini, Antigravity, and other agentic coding tools.
keywords:
  - ai-agents
  - codex
  - gemini
  - claude
  - cursor
  - antigravity
  - agentic-coding
  - developer-tools
  - governance
  - template
  - automation
  - ci
---

# ai-cockpit-template

[中文](README.zh-CN.md) | [日本語](README.ja.md)

`ai-cockpit-template` is a language-agnostic AI governance scaffold for engineering teams that use Codex, Gemini, Antigravity, or other coding agents. It adds a repeatable cockpit around AI-assisted code changes: define the task boundary first, keep the agent inside scope, require verification, summarize the change, and preserve an audit trail.

## Who It Is For

- Teams adopting AI coding agents in production repositories.
- Maintainers who want AI-generated diffs to be bounded, reviewable, and reversible.
- Engineers who need the same AI workflow across Rust, Flutter, TypeScript, Python, or mixed-language codebases.
- Organizations that want lightweight governance without adding a service, database, or proprietary runtime.

## Problem It Solves

AI agents can move fast, but they can also drift outside the requested task, delete tests, rewrite unrelated files, skip verification, or leave reviewers guessing what changed. This template turns each AI task into an explicit Work Item with machine-checkable scope, required checks, and a final summary.

## Design Philosophy

Human civilization repeatedly builds systems, lets those systems evolve, and eventually reaches a point where the system's complexity exceeds direct human control. At that point, complexity must be compressed: the internal process becomes a black box, and the cockpit returns the state that humans need in order to act.

I designed this framework for the AI development problem in front of me. The idea itself is not new, and it was not copied from aviation. When I solved the same control problem seriously, the same shape naturally appeared.

Strong systems are always controlled through layers: plan, boundary, verification, record, and status display. AI development needs the same layers:

| AI development problem | Required control layer | Aviation analogy |
| --- | --- | --- |
| The work plan is vague. | Work Item Contract | Flight plan |
| The change boundary is unclear. | Scope Guard | Controlled airspace |
| Verification is insufficient. | Required checks | Instrument check |
| Records are not preserved. | Change Summary and archive | Black box |
| Current state is invisible. | Cockpit Status | Cockpit |

The result naturally resembles an aviation control system: not because the structure was imported, but because the underlying problem is the same.

## Supported Agent Environments

- Codex: `AGENTS.md`
- Gemini: `GEMINI.md`
- Claude: `CLAUDE.md`
- Cursor: `.cursor/rules/ai-cockpit.mdc`
- Antigravity and other agents: use the same Contract, Summary, Makefile, and guard workflow.

## What It Provides

- Work Item Contract: the task boundary before an AI agent changes files.
- Scope Guard: blocks changes outside the declared scope.
- Backtrack Guard: reports undeclared removal of tests, snapshots, or Work Item records.
- Coverage Guard: reports production changes without matching test changes.
- Change Summary: records what changed, what was verified, and what risk remains.
- Cockpit Status: a generated one-screen view of the current AI task state.
- Finish Flow: validates checks and archives the Work Item only after the workflow passes.
- Installer: a non-destructive installer for adding AI Cockpit to existing repositories.

## Repository Layout

```text
.ai/
  cockpit/
    README.md
    checks.yaml
    current_status.md
  guards/
    backtrack_policy.yaml
    cockpit_status_policy.yaml
    coverage_policy.yaml
    file_boundary.yaml
    file_ownership.yaml
    scope_policy.yaml
    summary_policy.yaml
  work-items/
    _templates/
      work_item_contract.example.json
      work_item_summary.example.json
    active/
    archive/
.cursor/
  rules/
    ai-cockpit.mdc
examples/
  csharp/
  flutter/
  go/
  java/
  kotlin/
  php/
  python/
  ruby/
  rust/
  swift/
  typescript/
scripts/
  ai_archive_work_item.py
  ai_check_backtrack.py
  ai_check_coverage_guard.py
  ai_check_guards.py
  ai_check_scope.py
  ai_check_status.py
  ai_check_summary.py
  ai_check_work_item.py
  ai_common.py
  ai_finish.py
  ai_generate_status.py
  ai_observability.py
  ai_start.py
  install_ai_cockpit.py
templates/
  make/
    Makefile.ai
  stacks/
    flutter.mk
    go.mk
    generic.mk
    java.mk
    kotlin.mk
    php.mk
    python.mk
    ruby.mk
    rust.mk
    swift.mk
    typescript.mk
install.sh
Makefile
AGENTS.md
CLAUDE.md
GEMINI.md
```

## Quick Start

Use this repository directly as a GitHub template for new projects, or install AI Cockpit into an existing repository.

### Install Into An Existing Repository

From a local clone of this template:

```sh
/path/to/ai-cockpit-template/install.sh --stack rust
```

Remote one-command install:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

Safer two-step remote install:

```sh
curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh -o install-ai-cockpit.sh
sh install-ai-cockpit.sh --stack rust
```

Supported stack presets:

```text
generic
rust
flutter
typescript
python
go
java
kotlin
swift
ruby
php
csharp
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
- It appends AI Cockpit sections to existing `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md`.
- It installs Cursor rules under `.cursor/rules/ai-cockpit.mdc`.
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

The installer writes `Makefile.ai.stack`. Stack presets configure these command variables:

```make
PROJECT_FORMAT_CHECK = printf '%s\n' 'No formatter configured.'
PROJECT_TEST = printf '%s\n' 'No test command configured.'
PROJECT_LINT = printf '%s\n' 'No linter configured.'
```

Rust:

```make
PROJECT_FORMAT_CHECK = cargo fmt --all -- --check
PROJECT_TEST = cargo test
PROJECT_LINT = cargo clippy --all-targets -- -D warnings
```

Flutter:

```make
PROJECT_FORMAT_CHECK = dart format --set-exit-if-changed .
PROJECT_TEST = flutter test
PROJECT_LINT = flutter analyze
```

TypeScript:

```make
PROJECT_FORMAT_CHECK = npm run format:check
PROJECT_TEST = npm test
PROJECT_LINT = npm run lint
```

Python:

```make
PROJECT_FORMAT_CHECK = python3 -m ruff format --check .
PROJECT_TEST = python3 -m pytest
PROJECT_LINT = python3 -m ruff check .
```

Go:

```make
PROJECT_FORMAT_CHECK = test -z "$$(gofmt -l .)"
PROJECT_TEST = go test ./...
PROJECT_LINT = go vet ./...
```

Java / Kotlin:

```make
PROJECT_FORMAT_CHECK = ./gradlew spotlessCheck
PROJECT_TEST = ./gradlew test
PROJECT_LINT = ./gradlew check
```

Swift:

```make
PROJECT_FORMAT_CHECK = swift format lint --recursive .
PROJECT_TEST = swift test
PROJECT_LINT = swift build -Xswiftc -warnings-as-errors
```

Ruby:

```make
PROJECT_FORMAT_CHECK = bundle exec rubocop --format simple
PROJECT_TEST = bundle exec rake test
PROJECT_LINT = bundle exec rubocop
```

PHP:

```make
PROJECT_FORMAT_CHECK = vendor/bin/php-cs-fixer fix --dry-run --diff
PROJECT_TEST = vendor/bin/phpunit
PROJECT_LINT = vendor/bin/phpstan analyse
```

C#:

```make
PROJECT_FORMAT_CHECK = dotnet format --verify-no-changes
PROJECT_TEST = dotnet test
PROJECT_LINT = dotnet build -warnaserror
```

You can also update `.ai/cockpit/checks.yaml` so agents know which checks to choose for each task.

## Guard Configuration

- `.ai/guards/file_ownership.yaml` controls restricted and forbidden AI writes.
- `.ai/guards/file_boundary.yaml` blocks generated and runtime artifacts from entering code diffs.
- `.ai/guards/coverage_policy.yaml` defines production and test path patterns.
- `.ai/guards/scope_policy.yaml` defines paths that are always allowed and optional dependency scope rules.

The guard YAML parser intentionally supports a small subset of YAML so the scripts can run with Python's standard library only.

## Versioned Install

Use a tag for reproducible installs:

```sh
AI_COCKPIT_TEMPLATE_REF=v0.2.0 \
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

## Suggested Repository Topics

```text
ai-agents
codex
gemini
agentic-coding
developer-tools
governance
template
automation
ci
```

## Template Policy

Do not add business logic, personal paths, real API keys, GitHub secrets, or organization-specific runtime configuration to this repository. Keep examples generic and move real project policy into the adopting repository.
