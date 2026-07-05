---
author: Ray
title: "Roadmap"
description: AI Cockpit の長期進化ロードマップ（V1〜V4）。
keywords:
  - ai-cockpit
  - roadmap
  - governance
  - intent-aware
  - repository-intelligence
---

# ロードマップ (Roadmap)

AI Cockpit は AI アシスト型ソフトウェア開発のためのリポジトリガバナンスレイヤーです。本ドキュメントでは、プロジェクトの長期的なアーキテクチャ方向性を V1〜V4 の進化ステージとして定義します。

各バージョンは前バージョンのガバナンスを**拡張**するものであり、**置き換え**るものではありません。

---

## Core Positioning

**AI Cockpit is not an Agent Runtime. It is not a Workflow Engine.**

**AI Cockpit is a Repository Governance Layer for AI-assisted Software Development.**

It provides:

- **Governance**: Scope boundaries, verification requirements, and policy enforcement
- **Repository Context**: Explicit intent, constraints, and architectural knowledge
- **Verification**: Independent validation of changes against declared contracts
- **Auditability**: Complete records of what changed, why, and how it was verified
- **Intent**: First-class representation of why work exists, not just what to implement

AI Cockpit does not replace Claude Code, Codex, Cursor, Gemini CLI, or other agents. Agents evolve continuously. Governance should remain stable.

---

## Design Principles

These four principles guide all architectural decisions and roadmap phases:

### 1. Model Agnostic

AI Cockpit does not bind to any specific model or vendor. It supports Claude, GPT, Gemini, Codex, and future agents equally through stable, language-neutral governance contracts.

### 2. Stable Schema

Schema evolution is conservative and backward-compatible. We prioritize adding optional fields over breaking changes. Long-term stability enables trust.

### 3. Governance Over Workflow

AI Cockpit defines Repository Governance, not Agent Workflow. Workflows belong to agents and evolve with model capabilities. Governance remains stable and agent-agnostic.

### 4. Intent-driven Development

Implementation should be driven by Intent, not only by tasks. AI agents should understand:

- **Why** the work exists
- **What constraints** must be respected
- **What problems** should not be solved in this scope
- **Why this approach** was chosen

Intent becomes the foundation of the complete governance loop.

---

## The Governance Loop

AI Cockpit establishes a complete governance closed loop:

```text
Intent
  ↓
Contract
  ↓
Implementation
  ↓
Verification
  ↓
Summary (Intent Alignment)
```

This is not:
```text
Contract → Implementation → Verification
```

But rather:
```text
Intent → Contract → Implementation → Verification → Summary (validates alignment back to Intent)
```

The loop answers:
- **Intent**: Why does this work exist?
- **Contract**: What should change?
- **Implementation**: What actually changed?
- **Verification**: Does it meet requirements?
- **Summary**: Did we achieve the intended goal?

This governance loop is the architectural foundation for all V1–V4 evolution phases.

---

## V1 — Governance Foundation（deployed）

**目的**: AI アシスト型コーディングに対してリポジトリレベルのガバナンスを提供する。

**現行機能**:

| 機能 | 役割 |
|------|------|
| Work Item Contract | タスクの境界と検証要件を定義する契約 |
| Scope Guard | 範囲外の変更を検出 |
| Verification | 必須チェックの実行と結果記録 |
| AI Change Summary | 変更結果と検証エビデンスの構造化された記録 |
| Cockpit Status | リポジトリの現在の稼働状態の可視化 |
| Review Readiness | レビュー可能状態の判定 |

**このレイヤーが回答する問い**:

- 何が変更されるべきか？
- 要求された作業は完了したか？
- リポジトリはまだ安全か？

---

## V2 — Intent-aware Development（current milestone）

**Purpose**: Make Intent a first-class governance object. AI understands not only "**what** to change" but "**why** the change exists."

**Key Insight**: Intent is not a subsection of Contract. Intent **drives** Contract.

The governance flow becomes:

```text
Intent (first-class governance object)
  ↓
Work Item Contract (scope driven by intent)
  ↓
Implementation
  ↓
Verification
  ↓
Summary (Intent Alignment validation)
```

### Contract Schema Enhancement

The V2 Contract introduces an `intent` section as a top-level node:

```json
{
  "contractVersion": 2,
  "intent": {
    "businessGoal": "Optional: Business objective",
    "userGoal": "Optional: User-facing goal",
    "problem": "Optional: Detailed problem context",
    "constraints": ["Optional: Constraints to respect"],
    "nonGoals": ["Optional: What not to solve"],
    "rationale": "Optional: Why this approach"
  },
  "scope": [...],
  "acceptance": [...],
  ...
}
```

**Design Decisions**:

- **All fields are optional**: Repositories should not be forced to fill every field
- **Fully backward-compatible**: V1 Contracts remain valid
- **Natural adoption**: Fields most naturally used in current AI workflows (`problem`, `constraints`, `rationale`) will be adopted first; other fields enable future workflow evolution without schema changes
- **Intent as Concept, not File**: Intent is a governance object within the Contract, not a separate file format

### Summary Enhancement

Summary gains a new section: **Intent Alignment**

Example:
```json
{
  "intentAlignment": {
    "problemResolved": true,
    "constraintsRespected": true,
    "nonGoalsAvoided": true,
    "rationaleValidated": "Approach worked as expected"
  }
}
```

Summary no longer only answers "What changed?" but also "Did we achieve the intended goal?"

### problemStatement Relationship

The existing `problemStatement` field remains:

- `problemStatement`: One-line summary
- `intent.problem`: Detailed context and background

Both coexist. Future versions may deprecate `problemStatement` if `intent.problem` proves sufficient, but V2 preserves both for compatibility.

### Future Direction

**Checker (V3 consideration)**: Future versions may validate implementation against declared intent automatically. Example:

- Intent declares: `constraints: ["No API changes"]`
- Implementation modifies API
- Checker flags: "Intent Conflict Detected"

V2 establishes the schema. V3+ can build validation tooling.

---

## V3 — Repository Intelligence

**Purpose**: Accumulate long-term repository engineering knowledge beyond individual tasks.

**Target Knowledge**:

- Architecture decisions and evolution
- Decision history and context
- Migration knowledge and patterns
- Known pitfalls and anti-patterns
- Engineering conventions and practices
- Why the codebase is the way it is today

**Goal**: Enable AI agents to operate with understanding of repository history and context, not just task-level instructions.

**Relationship to V2**: V2's Intent provides task-level "why." V3 extends this to repository-level "why" — capturing architectural decisions, historical context, and organizational knowledge that should inform all future work.

---

## V4 — Organization Governance

**Purpose**: Extend repository-level governance to organization-level governance.

**Target Policies**:

- Engineering standards
- Security policies
- Architecture policies
- Compliance requirements
- Review standards
- Cross-repository conventions

**Goal**: Enable AI agents to respect organization-wide rules consistently across multiple repositories.

**Relationship to V2/V3**: V2 establishes Intent as first-class. V3 extends Intent to repository knowledge. V4 extends governance to organization-wide policy that multiple repositories share.

---

## Implementation Strategy

### Incremental Evolution

AI Cockpit evolves through small, backward-compatible steps. Each roadmap phase should:

- Preserve existing workflows
- Avoid breaking schema changes
- Introduce optional capabilities first
- Validate value before expanding scope

### Current Active Milestone

**V2 — Intent-aware Development**

Implementation proceeds in four incremental phases:

1. **Roadmap Documentation**: Establish architectural positioning and design principles
2. **Contract Schema**: V2 schema already deployed; documentation alignment only
3. **Validator Compatibility**: Ensure all validators handle optional intent fields correctly
4. **Templates & AI Integration**: Update templates and agent guidance to leverage intent naturally

See [V2 Implementation Plan](reference/v2-implementation-plan.md) for detailed phase breakdown.

---

## 関連ドキュメント

- [設計思想 (Design Philosophy)](philosophy/design-philosophy.md)
- [アーキテクチャ (Architecture)](architecture.md)
- [Contract フィールドリファレンス](contract-fields.md)
