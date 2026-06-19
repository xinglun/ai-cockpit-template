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

- AI-generated changes should not be accepted without bounded, independently enforced review.
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

The idea is simple: AI-generated changes need bounded, independently enforced review. AI Cockpit checks diffs after writes; it is not a filesystem permission boundary.

AI Cockpit adds a lightweight workflow around AI-generated changes:

- Work Item Contract: declare scope before the agent edits files
- Scope Guard: detect out-of-scope changes and block finish/archive/merge gates
- Backtrack Guard: report deleted tests/snapshots/work-item records
- Change Summary: require the agent to say what changed and what passed
- Cockpit Status: show the current task state in one generated file
- Finish Flow: archive the work item only after checks pass

It is language-agnostic and installs with:

AI_COCKPIT_TEMPLATE_REF=v0.5.3 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.3/install.sh)" -- --stack rust --update-makefile --create-adoption

Supported agents: Codex, Gemini, Claude, Cursor, Antigravity, and others.
Supported stack presets: Rust, Flutter, TypeScript, Python, Go, Java, Android, Kotlin, Swift, Ruby, PHP, C#. Presets require project-specific quality commands and guard paths.

This is not another agent framework. It is a small change-control layer for AI-assisted development.
```

## X / Twitter

```text
AI-generated changes should not be accepted without bounded, independently enforced review.

I built AI Cockpit: lightweight change governance for coding agents.

Contract -> Guard -> Summary -> Cockpit Status -> Archive

AI changed 37 files. Cockpit stopped the merge.
```

## dev.to Article Outline

Title:

```text
AI-generated changes should not be accepted without bounded, independently enforced review
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
