---
author: Ray
title: "AI Cockpit"
description: Language-agnostic AI governance template for Codex, Gemini, Claude, Cursor, Antigravity, and other agentic coding tools.
keywords:
  - ai-agents
  - ai-agent
  - ai-workflow
  - code-review
  - llmops
  - ai-safety
  - codex
  - gemini
  - claude
  - cursor
  - antigravity
  - agentic-coding
  - developer-tools
  - developer-workflow
  - governance
  - template
  - automation
  - ci
---

# AI Cockpit

[中文](README.zh-CN.md) | [日本語](README.ja.md)

AI coding agents can:

- rewrite unrelated files
- silently remove tests
- bypass verification
- leave reviewers guessing

Your AI agent should not have root access to your repository.

AI Cockpit is AI Change Governance for coding agents.

It adds a lightweight AI review workflow to AI-assisted development.

![AI Cockpit demo](docs/assets/ai-cockpit-demo.gif)

**AI changed 37 files. Cockpit stopped the merge.**

AI Cockpit makes AI-generated changes bounded, reviewable, and auditable.

I kept seeing AI rewrite unrelated files, roll back completed work, and bypass review expectations. So I built a small change-control workflow around scope, checks, summaries, and status.

## 30-Second Version

Before:

```text
AI changed 24 files.
Nobody knows why.
Tests may have disappeared.
Review starts from confusion.
```

After:

```text
Task scope declared.
Checks enforced.
Summary generated.
Cockpit updated.
Review starts from context.
```

## 3-Minute Install

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

Start a governed AI task:

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

Finish it with checks and an audit trail:

```sh
make ai-finish TASK=example_change
```

## How It Works

```text
Plan -> Scope -> Verify -> Summarize -> Status -> Archive
```

| Layer | What it does |
| --- | --- |
| Work Item Contract | Declares the task boundary before AI changes files. |
| Scope Guard | Blocks changes outside the declared scope. |
| Backtrack Guard | Blocks protected test, snapshot, or Work Item record deletion by default. |
| Coverage Guard | Blocks configured production changes without matching test changes by default. |
| Agent Risk Guard | Hard gate against prompt-is-advice, mid-task drift, and unknown-overclaim risks. |
| AI Review Policy | Flags governance and CI changes that need explicit review focus. |
| Checkpoint | Mid-task snapshot to detect scope drift before finishing. |
| Status Consistency Guard | Verifies Cockpit status matches the current set of active Work Items. |
| Change Summary | Records what changed, what was verified, and what risk remains. |
| Cockpit Status | Shows the current AI task state in one generated view. |
| Finish Flow | Archives the Work Item only after checks pass. |

## Trust Model

- `ai-start` records `baseCommit` and fingerprints pre-existing dirty paths.
- Guards inspect committed changes from `baseCommit...HEAD` plus staged, unstaged, and untracked changes. CI can set `AI_BASE_COMMIT` to the PR merge-base.
- Contracts reference registered check IDs; they cannot supply executable command strings. Registered checks resolve through `.ai/cockpit/checks.yaml` to explicit Make targets.
- `ai-finish` records the resolved check ID, exit code, duration, timestamp, execution commit, Contract hash, normalized command hash, output digest, and redacted output summary.
- These fields are structured execution records, not cryptographic or tamper-proof attestations. CI revalidates every changed archive pair and the complete PR diff.
- Restricted/destructive approval fields are self-declared workflow records. Trusted human approval must come from an external boundary such as CODEOWNERS review, a protected CI environment, or platform identity events.
- Active records stay local; successfully archived records are versionable audit artifacts under `.ai/work-items/archive/`.
- The installer ships the same PR validator and Make targets as this template. CI runs `make check-ai-pr AI_BASE_COMMIT=<merge-base>` after Work Items are archived.
- Every non-exempt PR path must be both scoped and reported by the same archived Contract/Summary pair.

The generic stack intentionally fails `quality` until its formatter, test, and lint commands are configured. A no-op quality gate is not a gate.

Template contributors can install the regression-test dependency with `python3 -m pip install -r requirements-dev.txt`. Runtime governance scripts still use only the Python standard library.

AI Cockpit reduces accidental scope drift and makes review evidence explicit; it is not a security sandbox for a malicious agent that can modify repository policy. Run project tests or `make quality` as an independent required CI check in addition to `check-ai-pr`.

## What It Catches

```text
[BLOCKED]
Scope violation detected.

Unauthorized file modification:
- src/auth/payment.rs

Allowed scope:
- src/auth/session.rs
- tests/auth/session_test.rs
```

## Supported

Agents:

```text
Codex, Gemini, Claude, Cursor, Antigravity, and other coding agents
```

Stacks:

```text
generic, rust, flutter, typescript, python, go, java, kotlin, swift, ruby, php, csharp
```

## Runtime Requirements

- Python 3.10 or higher.
- Git environment with support for merge-base and three-dot diffs (`...`).
- POSIX-compliant shell and GNU Make execution environment.
- Linux and macOS are officially supported for local execution and CI. Native Windows shells are not supported; please run inside WSL (Windows Subsystem for Linux) or another POSIX terminal.

## Advanced Docs

- [Installation](docs/installation.md)
- [Concept Guide (Japanese)](docs/overview.ja.md)
- [Contract & Summary Fields Manual](docs/contract-fields.md)
- [Configuration](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Design Philosophy](docs/design-philosophy.md)
- [Case Study: Stopping AI Rollback Corruption](docs/case-study-ai-rollback-corruption.md)
- [Promotional Material](docs/launch.md)
- [GitHub Topic Recommendations](docs/topics.md)
- [Language Examples](examples/)
