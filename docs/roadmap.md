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

## V2 — Intent-aware Development（completed）

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
- **Common adoption**: Fields most often used in current AI workflows (`problem`, `constraints`, `rationale`) are expected to be filled first; other fields keep room for workflow evolution without schema changes
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

### Next Consideration

**Checker (V3 consideration)**: Future versions may validate implementation against declared intent automatically. Example:

- Intent declares: `constraints: ["No API changes"]`
- Implementation modifies API
- Checker flags: "Intent Conflict Detected"

V2 establishes the schema. V3+ can build validation tooling.

---

## V2.5 — Governance Compression（implemented, stabilizing）

**Purpose**: Convert repository truth into human decision state.

V2.5 positions Cockpit as the layer that consumes governance records and presents a concise operational state for human review.

The governance flow becomes:

```text
Intent
  ↓
Contract
  ↓
Implementation
  ↓
Verification
  ↓
Summary (Repository Truth)
  ↓
Cockpit (Governance Compression)
  ↓
Human Decision
```

### Key Shift

V2.5 is not primarily an AI completion feature. It is a human review feature.

The four layers have distinct responsibilities:

| Layer | Question |
| --- | --- |
| Intent | Why do this? |
| Contract | How should this be done? |
| Summary | What actually happened? |
| Cockpit | What decision should a human make now? |

Summary should continue becoming a complete audit record. Cockpit should compress that repository truth into decision-oriented signals such as Intent resolved, Acceptance complete, Unknowns resolved, Verification passed, Residual risk low, and Recommendation ready for review.

Before V3 is considered, V2.5 should be stabilized against real Work Items and reviewer-facing examples. The practical reference for that calibration is [How to Read Cockpit Status](reference/how-to-read-cockpit-status.md).

Completion Assurance becomes one component of Governance Compression rather than the milestone name.

See [V2.5 Governance Compression Plan](reference/v2-5-governance-compression-plan.md) for the implemented reference plan.

---

## V2.6 — Scenario Coverage / Risk Domain Scenario Matrix（current capability）

**Purpose**: Add a generic Scenario Coverage layer so medium/high-risk Work Items can prove which risk-domain scenarios were verified, which remain unverified, and which are not_applicable.

V2.6 does not add built-in release/auth/installer scenario libraries to Core. It adds the mechanism, then lets each repository or Work Item provide its own scenario content.

The policy source for deciding when Scenario Coverage is required lives in `.ai/guards/scenario_coverage_policy.yaml`.

### Key Shift

V2.6 keeps `acceptance` as the task-completion contract, but adds a separate signal for risk-domain coverage. This prevents medium/high-risk tasks from looking clean when a reviewer still needs to inspect unverified scenarios.

### Scope Boundaries

- Add duplicate-key rejection for active JSON governance files.
- Add optional `scenarioCoverage` structures to Contract and Summary.
- Add `make check-ai-scenario-coverage` and wire it into Cockpit status.
- Keep `unknowns`, `residualRisks`, `followUps`, and `unverifiedScenarios` separate.
- Keep scenario content project-owned and language-neutral.

### Review Outcome

V2.6 aims to make medium/high-risk Work Items land in one of three reviewer states:

- fully covered and ready
- ready with explicitly acknowledged risks
- needs investigation because coverage is incomplete or too ambiguous

See the V2.6 implementation notes and reviewer-facing examples in the Cockpit docs and Work Item templates.

---

## V2.6.5 — Preflight Review / Evidence over Self-Declaration

**Purpose**: Show implementation readiness before coding starts by deriving a Preflight Review from existing Work Item Contract evidence.

V2.6.5 does not ask the AI whether it feels ready. It exposes whether the repository record supports implementation by reading the Contract fields that already exist: `intent`, `unknowns`, `sources`, `acceptance`, `scope`, `outOfScope`, `riskAssessment`, `scenarioCoverage`, and `verification`. It also reads explicit blocker fields: `notCodable: true`, `executionDecision.status` of `block`, `defer`, or `needs_human_decision`, and an `agentCapability` that cannot implement or verify or needs a human decision. Any of those explicit blockers derives `not_ready` directly.

The review is advisory by default and becomes a gate only when policy explicitly enables that behavior. The workflow rule is separate from exit codes: when the review is `needs_human_confirmation` or `not_ready`, the agent must pause and report the review before implementation continues.

### Key Shift

V2.6.5 keeps Cockpit Status as reviewer visibility, but adds a pre-implementation pause rule for agent workflows. That keeps the evidence visible without turning the default flow into a hard stop.

### Scope Boundaries

- Add a generic Preflight Review view derived from existing Contract evidence.
- Keep the output advisory by default and configurable as a gate.
- Keep the logic generic and repository-neutral.
- Keep Cockpit Status readable for reviewers without making it a substitute for pre-implementation pause.

### Review Outcome

V2.6.5 aims to make implementation start with the evidence already surfaced, so reviewers can see `ready`, `needs_human_confirmation`, or `not_ready` before code changes begin.

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

### Completed Milestones

**V2 — Intent-aware Development**

Implementation completed in four incremental phases:

1. **Roadmap Documentation**: Establish architectural positioning and design principles
2. **Contract Schema**: V2 schema already deployed; documentation alignment only
3. **Validator Compatibility**: Ensure all validators handle optional intent fields correctly
4. **Templates & AI Integration**: Update templates and agent guidance to leverage intent naturally

See [V2 Implementation Plan](reference/v2-implementation-plan.md) for the completed phase breakdown.

**V2.5 — Governance Compression (implemented, stabilizing)**

V2.5 established the human review compression layer that turns Summary evidence into operational recommendations.

V2.6 extends that layer with generic Scenario Coverage for medium/high-risk Work Items.

See [V2.5 Governance Compression Plan](reference/v2-5-governance-compression-plan.md) for the implemented reference plan.

---

## 関連ドキュメント

- [設計思想 (Design Philosophy)](philosophy/design-philosophy.md)
- [アーキテクチャ (Architecture)](architecture.md)
- [Contract フィールドリファレンス](contract-fields.md)
