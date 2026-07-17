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
android
kotlin
swift
ruby
php
csharp
```

## Project Checks

<!-- stack-tiers: verified=python,go,rust,typescript,java,kotlin,ruby,php,csharp,flutter,android,swift; workflow-implemented=; preset-only=generic -->

Compatibility evidence is tiered:

- **Hosted verification recorded:** `python`, `go`, `rust`, and `typescript` run minimal-project jobs in `real-stack-quality`. `java`, `kotlin`, `ruby`, `php`, and `csharp` run the same gate in `extended-real-stack-quality`. `flutter`, `android`, and `swift` run the same gate in `mobile-stack-quality`.
- **Preset only:** `generic` provides editable fail-closed commands but intentionally fails `ai-cockpit-quality` until configured.
- **Unsupported runtime/platform:** native Windows shells. Use WSL or another POSIX environment.

CI verification has two compatibility evidence tiers. The fixed Python, shell, real-stack, extended-stack, and mobile baseline lanes use declared tool versions and feed the release-blocking `compatibility-gate`. A separate `latest-ecosystem-probe` requests current Stable/Latest Python, Go, Node, Ruby, PHP, and Swift tools; it is summarized by the non-blocking `compatibility-latest` job and may warn when the ecosystem moves. The `ubuntu-latest` and `macos-latest` hosted labels are moving infrastructure, not pinned platform versions. Neither tier guarantees compatibility with every framework version, plugin set, monorepo layout, SDK, or generated-code policy.

Stack presets populate these variables:

```make
PROJECT_FORMAT_CHECK = printf '%s\n' 'No formatter configured.'
PROJECT_TEST = printf '%s\n' 'No test command configured.'
PROJECT_LINT = printf '%s\n' 'No linter configured.'
```

Those lines illustrate variable names only. The shipped generic preset fails closed until all three commands are configured; it does not treat placeholder output as a successful quality gate.

Presets are editable starting points rather than dependency installers or universal compatibility guarantees. Before using one, make sure its formatter, test runner, SDK, and build plugins are configured in the target repository. Compatibility CI uses JDK 21 for Java and JDK 17 for the Android smoke project; neither value is a universal project requirement. AI Cockpit does not install, switch, or version-manage JDKs: use the version required by the project's Gradle Wrapper and Android Gradle Plugin (AGP). For Android projects, the preset task names are calibration starting points: replace `testDebugUnitTest`, `spotlessCheck`, and `lint` with the actual `test<Flavor><BuildType>UnitTest` and `lint<Variant>` commands exposed by the Gradle wrapper. The Python preset expects Ruff and pytest. `examples/` demonstrates selected stacks and does not mirror every available preset.

Stack selection changes quality commands only; it does not install a stack-specific guard policy. The default Coverage Guard includes several common layouts (`src/`, `lib/`, Android `app/src/main/`, Swift `Sources/`, and C# files), but repositories must review production/test patterns and `associations` in `.ai/guards/coverage_policy.yaml` before treating the gate as complete framework coverage. Android adopters should keep that policy report-only at first, then narrow module and flavor boundaries after the real source-set layout is confirmed.

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

Coverage associations are named mappings with `production` and `tests` pattern lists. Test patterns may use `{stem}`, `{module}`, `{name}`, and `{dir}`, derived from each changed production path. A production path fails closed when it matches no association or when no changed test path matches its expanded association. This proves path-level pairing only; it does not inspect source content, execute tests, or prove semantic/runtime coverage.

```yaml
associations:
  authentication:
    production:
      - "src/auth/**"
    tests:
      - "tests/auth/**"
      - "tests/test_{stem}.py"
```

Restricted paths are hard failures unless the active Contract contains an explicitly approved `restrictedWriteApproval` with an approver and reason. `destructiveChangePolicy.allowPatterns` is inactive unless destructive changes are allowed and any required human approval evidence is present.

These approval objects are explicit workflow records, not trusted identity assertions: an agent that can edit the Contract can also edit those fields. The template repository is maintained by personal Code Owner `@RayIori`; an installed target project must replace that identity and enforce at least one required approval outside the Contract. This does not claim organization-Team or two-independent-maintainer assurance. Organizations that require stronger trustworthy approval must enforce it through a visible `@org/team` CODEOWNERS entry, required reviews, protected environments, or CI checks backed by platform identity.

`scope_policy.yaml` `dependencyScopeRules` maps a changed source pattern to required companion change patterns. The default policy requires governance script changes to include tests.

For pull-request CI, set `AI_BASE_COMMIT` to `git merge-base HEAD <target-branch>`. This makes every diff-aware guard inspect committed PR changes in a clean checkout.

For Android and Java projects, keep CI staged: use `make check-ai-pr` as the first blocking check once the Gradle wrapper and preset task names are calibrated, then add `make ai-cockpit-quality` as a separate L2 gate after the variant-specific tasks and coverage boundaries are stable.

The lifecycle permits one active Work Item per worktree. A branch may archive several serial Work Items before commit. CI validates every changed archive pair against the full PR diff, and each non-exempt path must be both in one Contract's scope, outside that Contract's outOfScope, and in its paired Summary's `changedFiles`. Cross-pair scope/report claims do not satisfy ownership. Use separate worktrees for truly parallel Work Items.

Version 2 Contracts list `verification[].check` IDs only. Add or approve executable checks in `.ai/cockpit/checks.yaml`; each command must invoke an explicit Make target. Raw Contract command strings are rejected.

`check-ai-pr` validates governance records and the complete diff but does not rerun every historical project check. Configure project tests or `make ai-cockpit-quality` as a separate required CI job.

## Agent Environments

- Codex: `AGENTS.md`
- Gemini: `GEMINI.md`
- Claude: `CLAUDE.md`
- Cursor: `.cursor/rules/ai-cockpit.mdc`
- Antigravity and other agents: use the same Contract, Summary, Makefile, and guard workflow.
