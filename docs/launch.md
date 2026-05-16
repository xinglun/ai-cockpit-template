---
author: Ray
title: "Launch Copy"
description: Launch copy for sharing AI Cockpit on Reddit, Hacker News, X, and dev.to.
keywords:
  - ai-cockpit
  - launch
  - hacker-news
  - reddit
  - devto
  - ai-change-governance
---

# Launch Copy

## One-Line Positioning

AI Cockpit is AI Change Governance for coding agents.

## Short Punchlines

- Your AI agent should not have root access to your repository.
- AI changed 37 files. Cockpit stopped the merge.
- Git-style discipline for AI-generated changes.
- Stop reviewing AI diffs blind.
- Make AI changes bounded, reviewable, and auditable.

## Hacker News / Reddit

Title:

```text
Show HN: AI Cockpit — lightweight change governance for coding agents
```

Post:

```text
I built AI Cockpit after repeatedly seeing AI coding agents rewrite unrelated files, silently remove tests, roll back completed work, and leave reviewers guessing what happened.

The idea is simple: AI should not have root access to your repository.

AI Cockpit adds a lightweight workflow around AI-generated changes:

- Work Item Contract: declare scope before the agent edits files
- Scope Guard: block changes outside the declared boundary
- Backtrack Guard: report deleted tests/snapshots/work-item records
- Change Summary: require the agent to say what changed and what passed
- Cockpit Status: show the current task state in one generated file
- Finish Flow: archive the work item only after checks pass

It is language-agnostic and installs with:

sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust

Supported agents: Codex, Gemini, Claude, Cursor, Antigravity, and others.
Supported stacks: Rust, Flutter, TypeScript, Python, Go, Java, Kotlin, Swift, Ruby, PHP, C#.

This is not another agent framework. It is a small change-control layer for AI-assisted development.
```

## X / Twitter

```text
Your AI agent should not have root access to your repository.

I built AI Cockpit: lightweight change governance for coding agents.

Contract -> Guard -> Summary -> Cockpit Status -> Archive

AI changed 37 files. Cockpit stopped the merge.
```

## dev.to Article Outline

Title:

```text
Your AI agent should not have root access to your repository
```

Outline:

```text
1. AI coding agents are useful, but the diff can drift.
2. The real problem is not generation. It is change governance.
3. The failure mode: unrelated rewrites, silent test deletion, rollback corruption.
4. The control layer: Contract, Guard, Summary, Status, Archive.
5. A blocked example: unauthorized file modification.
6. Install AI Cockpit and run the first Work Item.
7. What I am intentionally not building yet: cloud dashboard, orchestration, enterprise platform.
```

