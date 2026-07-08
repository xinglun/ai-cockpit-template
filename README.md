---
author: Ray
title: "AI Cockpit"
description: Application-language-agnostic collaborative engineering environment and AI governance template for Codex, Gemini, Claude, Cursor, Antigravity, and other agentic coding tools.
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

AI-generated changes should not be accepted without bounded, independently enforced review.

## What is AI Cockpit?

**AI Cockpit is a Repository Governance Layer for AI-assisted Software Development.**

It is **not** an Agent Runtime. It is **not** a Workflow Engine.

It provides:

- **Governance**: Scope boundaries, verification requirements, policy enforcement
- **Repository Context**: Explicit intent, constraints, architectural knowledge
- **Verification**: Independent validation of changes against declared contracts
- **Auditability**: Complete records of what changed, why, and how it was verified
- **Intent**: First-class representation of why work exists, not just what to implement

AI Cockpit does not replace agents like Claude Code, Codex, Cursor, or Gemini CLI. Agents evolve continuously with model capabilities. **Governance should remain stable.**

AI Cockpit checks diffs after writes; it is not a filesystem permission boundary or security sandbox.

![AI Cockpit demo](docs/assets/ai-cockpit-demo.gif)

**AI changed 37 files. Cockpit stopped the merge.**

AI Cockpit makes AI-generated changes bounded, reviewable, and auditable.

I kept seeing AI rewrite unrelated files, roll back completed work, and bypass review expectations. So I built a governance layer around scope, checks, summaries, and status, with explicit contracts as the core control mechanism.

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

## Version Evolution

- **V2 - Intent-aware Development (completed)**: Work Item Contracts gained the optional `intent` node (`problem`, `constraints`, `rationale`, and related fields), so AI can understand not only what to change but why the work exists.
- **V2.5 - Governance Compression (implemented, stabilizing)**: Summary became Repository Truth and Cockpit became the Human Decision layer. Cockpit compresses repository evidence into decision-oriented signals such as `ready_for_review`, `ready_with_risks`, `needs_investigation`, and `blocked`.
- **V2.6 - Scenario Coverage (current capability)**: Medium/high-risk Work Items can record generic scenario coverage without hard-coding release/auth/installer scenario libraries into Core. Scenario content stays in the Work Item, and the policy source lives in `.ai/guards/scenario_coverage_policy.yaml`.

<!-- install-prerequisites: python3.10,git-initial-commit,curl,gnu-make,posix -->

**Prerequisites:** Linux, macOS, or WSL with a POSIX shell; Python 3.10+; Git, curl, and GNU Make; and a clean Git repository with at least one commit. The selected stack's formatter, test runner, SDK, and build plugins must already be installed.

## Quick Install

Use this when you want the shortest path to a fresh adoption install. For the full lifecycle and page map, read [Installation](docs/getting-started/installation.md) and [Documentation Architecture](docs/reference/documentation-architecture.md).

```sh
ADOPTION_BASE="$(git rev-parse HEAD)"
STACK="${STACK:-generic}" # generic, python, go, rust, typescript, java, android, kotlin, flutter, swift, ruby, php, or csharp
RELEASE_TAG="$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/release.json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["releaseTag"])' 2>/dev/null || git ls-remote --tags --refs https://github.com/xinglun/ai-cockpit-template.git 'v*' | python3 -c 'import re,sys; tags=[m.group(1) for line in sys.stdin for m in [re.search(r"refs/tags/(v\d+\.\d+\.\d+)$", line)] if m]; print(max(tags, key=lambda tag: tuple(map(int, tag[1:].split(".")))))')"
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL "https://raw.githubusercontent.com/xinglun/ai-cockpit-template/${RELEASE_TAG}/install.sh" -o "$INSTALLER"
AI_COCKPIT_TEMPLATE_REF="$RELEASE_TAG" sh "$INSTALLER" --stack "$STACK" --update-makefile --create-adoption
make ai-finish TASK=adopt_ai_cockpit
git add .
git commit -m "adopt AI Cockpit governance"
make check-ai-pr AI_BASE_COMMIT="$ADOPTION_BASE"
CONFIG_BASE="$(git rev-parse HEAD)"
make ai-start TASK=configure_ai_cockpit TITLE="Configure AI Cockpit for this project" MODE=code
```

The command resolves a tagged installer from `release.json` when possible and falls back to the highest published semantic-version tag during the metadata rollout. It then downloads and executes only the resolved tagged installer.

Review and extend the generated configuration Contract scope before changing Project Profile, Guard, quality-command, or CI files. Then calibrate the installed runtime before enabling blocking gates:

<!-- governance-flow: install,configure-work-item,onboard,doctor,calibrate,confirm,validate,readiness,develop -->

```sh
make ai-onboard
# Or step by step:
make cockpit-doctor
make cockpit-calibrate
# Review .ai/project_profile.proposed.yaml, then create and approve .ai/project_profile.yaml.
make check-ai-project-profile
make check-ai-guard-calibration
make check-ai-adoption-ready
make ai-finish TASK=configure_ai_cockpit
git add .
git commit -m "configure AI Cockpit for this project"
make check-ai-pr AI_BASE_COMMIT="$CONFIG_BASE"
```

Doctor records detected facts, evidence, confidence, suggestions, and unknowns without changing project policy. Calibration creates only a proposal; it never overwrites Guards or approves high-risk paths. After explicit human confirmation and successful readiness checks, start a governed task:

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

Finish it with checks and an audit trail:

```sh
make ai-finish TASK=example_change
```

## How It Works

The governance loop:

```text
Intent → Contract → Implementation → Verification → Summary (Repository Truth) → Cockpit (Governance Compression) → Human Decision
```

| Layer | What it does |
| --- | --- |
| Intent | Declares why the work exists, constraints to respect, and rationale for the approach (optional but recommended). |
| Work Item Contract | Declares the task boundary before AI changes files. |
| Scope Guard | Detects changes outside the declared scope and blocks finish, archive, or merge gates. |
| Backtrack Guard | Detects protected test, snapshot, or Work Item record deletion and blocks configured gates. |
| Coverage Guard | Requires each configured production path to have a changed test path matched by a project-owned association rule; it does not inspect test contents or prove runtime coverage. |
| Scenario Coverage | Records generic risk-domain coverage for medium/high-risk Work Items using the policy in `.ai/guards/scenario_coverage_policy.yaml`. Scenario content stays in the Work Item. |
| Agent Risk Guard | Hard gate against prompt-is-advice, mid-task drift, and unknown-overclaim risks. |
| AI Review Policy | Flags governance and CI changes that need explicit review focus. |
| Checkpoint | Mid-task snapshot to detect scope drift before finishing. |
| Status Consistency Guard | Verifies Cockpit status matches the current set of active Work Items. |
| Change Summary | Records what changed, what was verified, what risk remains, whether intent was achieved, and any scenario coverage evidence. |
| Cockpit Status | Shows the current AI task state in one generated view, including the compressed scenario coverage signal. |
| Finish Flow | Archives the Work Item only after checks pass. |

## Core Principles

- **Intent-driven Development**: Work should be driven by declared intent (problem, constraints, rationale), not only by task descriptions
- **Evidence over reasoning**: Store verifiable evidence, not private reasoning
- **Machine-verifiable contracts**: Governance depends on structured, auditable records
- **Minimal process**: Add governance only where it prevents real failures
- **Scope-first engineering**: Declare boundaries before changing files
- **Backward compatibility by default**: Schema evolution is conservative
- **Explicit non-goals**: Document what should not be solved in this scope
- **Prefer extending existing concepts**: Avoid inventing new abstractions prematurely
- **Documentation before schema**: Design principles are documented before implementation

See also: [Work Item Style Guide](docs/work-item-style-guide.md), [Roadmap (V1–V4)](docs/roadmap.md)

AI Cockpit stores evidence, not reasoning. Reasoning guides the agent; evidence supports review, verification, and audit. Only reviewable evidence belongs in repository records.

Every new schema field should answer one question: what machine-verifiable evidence does this field preserve?

## Responsibility Model

| Layer | Responsibility |
| --- | --- |
| Human Intent | Why the work exists |
| Agent Thinking | How the task is interpreted |
| Reviewable Evidence | What the repository records |
| Repository Governance | What checks and policies validate |
| Repository History | What is preserved for audit and review |

Thinking can be rich and contextual, but repository records should preserve reviewable evidence. Governance checks operate on that evidence, not on private reasoning.

## Review Lenses

| Review Lens | AI Cockpit Surface |
| --- | --- |
| Empathy | `problemStatement`, `intent.problem`, `intent.constraints`, `intent.rationale`, `sources` |
| Design | `acceptance`, `guidelines` |
| Architecture | `scope`, `outOfScope`, `riskAssessment`, `rollbackNote` |
| Implementation | `mode`, actual diff, `changedFiles` |
| Judgment | `unknowns`, `notCodable`, `agentCapability`, `executionDecision`, `reviewReadiness` |
| Shipping | `verification`, `Summary`, `Cockpit Status`, `Archive` |

These are review lenses, not hard lifecycle phases.
The lenses explain how to review and reason about a task, not how the repository records private reasoning.
They do not replace `Plan -> Scope -> Verify -> Summarize -> Status -> Archive`.

Do not add `workflowPhase`.
Do not add `workflowEvidence`.
Do not require empathy, design, architecture, implementation, judgment, or shipping fields.
Agents must not invent missing user impact or business motivation.
Prefer explicit `not provided` over inferred explanations.

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

AI Cockpit reduces accidental scope drift and makes review evidence explicit; it is not a security sandbox for a malicious agent that can modify repository policy. For the public release selected above, run project tests or `make ai-cockpit-quality` as an independent required CI check in addition to `check-ai-pr`.

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
generic, rust, flutter, typescript, python, go, java, android, kotlin, swift, ruby, php, csharp
```

Compatibility levels:

<!-- stack-tiers: verified=python,go,rust,typescript,java,kotlin,ruby,php,csharp,flutter,android,swift; workflow-implemented=; preset-only=generic -->

- **Hosted verification recorded:** `python`, `go`, `rust`, and `typescript` run minimal-project jobs in `real-stack-quality`. `java`, `kotlin`, `ruby`, `php`, and `csharp` run the same gate in `extended-real-stack-quality`. `flutter`, `android`, and `swift` run the same gate in `mobile-stack-quality`.
- **Swift verified scope:** `mobile-stack-quality` exercises a minimal Swift Package Manager fixture only. Hosted verification does **not** cover Xcode projects, workspaces, or CocoaPods; those layouts require Project Calibration after installation.
- **Preset only:** `generic` intentionally fails closed until its formatter, test, and lint commands are configured.
- **Unsupported runtime/platform:** native Windows shells. Use WSL or another POSIX environment.

Stack presets are customizable starting points, not dependency installers. The selected project's formatter, test runner, SDK, and build plugins must already be available; for example, the Java and Android presets expect a Gradle wrapper and Spotless configuration, while Python expects Ruff and pytest. The examples directory covers selected stacks and does not currently include every preset.

The governance runtime is language-agnostic, but stack presets and default guard paths are not universal framework support. Review `Makefile.ai.stack` and `.ai/guards/coverage_policy.yaml` against the target repository before making them required CI gates.

Installation deploys the runtime; it does not complete production adaptation. The separate `configure_ai_cockpit` Work Item owns Project Profile, Guard, quality-command, and CI adaptation. Adoption readiness also requires an approved Project Profile, Profile/Guard consistency, non-placeholder quality commands, reviewed Coverage paths, and CI wiring for both `ai-cockpit-quality` and `check-ai-pr`. This is a static completeness check, not a security proof or proof that project commands are meaningful.

<!-- release-capabilities: auditable-adoption,sha256-verification -->
<!-- public-quality-target: ai-cockpit-quality -->

The current public release includes auditable first-adoption bootstrap and caller-provided SHA256 verification. Project-specific quality, Coverage paths, and CI still require explicit adaptation.

## Runtime Requirements

- Python 3.10 or higher.
- Git environment with support for merge-base and three-dot diffs (`...`).
- POSIX-compliant shell and GNU Make execution environment.
- Linux and macOS are officially supported for local execution and CI. Native Windows shells are not supported; please run inside WSL (Windows Subsystem for Linux) or another POSIX terminal.

Repository `make quality` runs the full test suite with a 60% overall script coverage floor and per-file regression floors for lifecycle-critical scripts, Ruff over `scripts/` and `tests/`, Mypy over all governance scripts, Bandit for medium/high findings, Python compilation, diff checks, and documentation consistency.

## Advanced Docs

- [Installation](docs/getting-started/installation.md)
- [First Work Item](docs/getting-started/first-work-item.md)
- [Roadmap (V1–V4)](docs/roadmap.md)
- [V2 Implementation Plan](docs/reference/v2-implementation-plan.md)
- [How to Read Cockpit Status](docs/reference/how-to-read-cockpit-status.md)
- [Concept Guide (Japanese)](docs/overview.ja.md)
- [Contract & Summary Fields Manual](docs/contract-fields.md)
- [Configuration](docs/configuration.md)
- [Non-Make Adaptation (Japanese)](docs/non-make-adaptation.ja.md)
- [Architecture](docs/architecture.md)
- [Documentation Architecture](docs/reference/documentation-architecture.md)
- [Design Philosophy](docs/philosophy/design-philosophy.md)
- [Case Study: Stopping AI Rollback Corruption](docs/case-study-ai-rollback-corruption.md)
- [Language Examples](examples/)
