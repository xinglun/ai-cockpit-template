---
author: Ray
title: "Configuration"
description: Stack and guard configuration reference for AI Cockpit.
keywords:
  - ai-cockpit
  - configuration
  - scope-guard
  - coverage-guard
  - makefile
---

# Configuration

AI Cockpit keeps project-specific commands in `Makefile.ai.stack`.

## Supported Stacks

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

## Project Checks

Stack presets configure these variables:

```make
PROJECT_FORMAT_CHECK = printf '%s\n' 'No formatter configured.'
PROJECT_TEST = printf '%s\n' 'No test command configured.'
PROJECT_LINT = printf '%s\n' 'No linter configured.'
```

Examples:

```make
# Rust
PROJECT_FORMAT_CHECK = cargo fmt --all -- --check
PROJECT_TEST = cargo test
PROJECT_LINT = cargo clippy --all-targets -- -D warnings

# TypeScript
PROJECT_FORMAT_CHECK = npm run format:check
PROJECT_TEST = npm test
PROJECT_LINT = npm run lint

# Go
PROJECT_FORMAT_CHECK = test -z "$$(gofmt -l .)"
PROJECT_TEST = go test ./...
PROJECT_LINT = go vet ./...
```

## Guard Configuration

- `.ai/guards/file_ownership.yaml` controls restricted and forbidden AI writes.
- `.ai/guards/file_boundary.yaml` blocks generated and runtime artifacts from entering code diffs.
- `.ai/guards/coverage_policy.yaml` defines production and test path patterns.
- `.ai/guards/scope_policy.yaml` defines paths that are always allowed and optional dependency scope rules.
- `.ai/guards/agent_risk_policy.yaml` defines hard gates for prompt-is-advice, mid-task drift, and unknown-overclaim risks.
- `.ai/guards/ai_review_policy.yaml` defines path patterns that require explicit review focus in the Change Summary (report-only).

The guard YAML parser intentionally supports a small subset of YAML so the scripts can run with Python's standard library only.

## Agent Environments

- Codex: `AGENTS.md`
- Gemini: `GEMINI.md`
- Claude: `CLAUDE.md`
- Cursor: `.cursor/rules/ai-cockpit.mdc`
- Antigravity and other agents: use the same Contract, Summary, Makefile, and guard workflow.

