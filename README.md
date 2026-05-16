---
author: Ray
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

AI Cockpit adds a lightweight AI review workflow to AI-assisted development.

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
| Backtrack Guard | Reports undeclared removal of tests, snapshots, or Work Item records. |
| Coverage Guard | Reports production changes without matching test changes. |
| Change Summary | Records what changed, what was verified, and what risk remains. |
| Cockpit Status | Shows the current AI task state in one generated view. |
| Finish Flow | Archives the Work Item only after checks pass. |

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

## Advanced Docs

- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Design Philosophy](docs/design-philosophy.md)
- [Suggested GitHub Topics](docs/topics.md)
- [Language examples](examples/)
