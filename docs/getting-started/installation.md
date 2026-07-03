---
author: Ray
title: "Installation"
description: Installation and quick start guide for AI Cockpit.
keywords:
  - ai-cockpit
  - installation
  - quick-start
  - ai-agents
---

# Installation

Install a fixed release of AI Cockpit into an existing repository. Start with the Quick Install entry in [README.md](../../README.md), then use this guide to confirm the repository is ready for adoption.

## Installation Flow

Use the same five-stage adoption flow until validation completes:

1. Pre-flight: confirm the repository is a clean Git work tree with the required toolchain.
2. Install: choose the stack preset and run the installer.
3. Adoption: finish the generated adoption Work Item and verify status.
4. Project Calibration: review the proposed project profile and guards.
5. Validation: confirm adoption readiness and cockpit status.

### Phase 1. Pre-flight

Before installing, run the checks that keep the installer from failing late:

```sh
git status --short
git rev-parse --is-inside-work-tree
git rev-list --count HEAD
python3 --version
command -v make
```

The work tree should be clean, the repository should already have at least one commit, Python must be 3.10 or newer, and `make` must resolve on `PATH`. If any check fails, fix the repository state first.

When you use `--create-adoption`, the installer prints **WARN** messages before it fails closed on a dirty worktree or on tracked hygiene files such as `.DS_Store`. Clean or untrack those files before retrying.

For Cursor users, the installed `.cursor/rules/ai-cockpit.mdc` defaults to `alwaysApply: false`. Enable **Always Apply** locally when you want governance on read-only sessions too.

### Phase 2. Install

Use the Quick Install entry in [README.md](../../README.md) and choose the stack that matches the target repository:

| Stack | When to choose it |
| --- | --- |
| `generic` | Default preset. It fails closed until you calibrate project-specific quality commands. Prefer this when a named stack preset would be misleading—for example, CocoaPods plus Xcode workspace layouts where `STACK=swift` suggests SPM-only commands. |
| `flutter` | Flutter applications and packages. |
| `python` | Python repositories. |
| `typescript` | JavaScript and TypeScript repositories. There is no separate `node` preset. |
| `go` | Go repositories. |
| `rust` | Rust repositories. |
| `java` | Java repositories. |
| `android` | Android projects. |
| `kotlin` | Kotlin projects. |
| `swift` | Swift Package Manager (SPM) projects. Xcode workspaces, `.xcodeproj` layouts, and CocoaPods require Project Calibration even when this preset is the starting point. |
| `ruby` | Ruby projects. |
| `php` | PHP projects. |
| `csharp` | C# and .NET projects. |

After installation, confirm that the target repository gained the expected files or updates:

- `.ai/`
- `Makefile.ai`
- `Makefile.ai.stack`
- `.cursor/rules/ai-cockpit.mdc`
- AI Cockpit sections in `AGENTS.md`, `GEMINI.md`, or `CLAUDE.md` when those files already exist
- `examples/` when `--with-examples` is used

You should not expect `templates/` to be copied into the target repository. That tree stays in the source template.

### Phase 3. Adoption

From a clean Git repository with at least one commit, finish the generated adoption Work Item and verify status:

```sh
make ai-finish TASK=adopt_ai_cockpit
make check-ai-status
git add .
git commit -m "adopt AI Cockpit governance"
make check-ai-pr AI_BASE_COMMIT='<pre-adoption-commit>'
```

The installer-generated Work Item owns every file actually written or appended by installation. It keeps project quality configuration as an explicit follow-up rather than recording generic placeholder commands as passed. `--create-adoption` fails before writing unless the repository has an initial commit, a clean worktree, and no active Work Item. `make check-ai-status` should report no active adoption Work Item before you move on.

### Local Calibration Checklist

AI Cockpit fits a **generic template plus local calibration** model. Installation deploys governance runtime and fail-closed defaults; it does not complete production adaptation. Use this checklist after Phase 3 Adoption and before treating the repository as production-ready:

1. **Two Work Items, two commits:** finish `adopt_ai_cockpit` in its own commit, then start `configure_ai_cockpit` for Profile, Guard, quality-command, and CI changes.
2. **Doctor facts, human approval:** review `target/ai_project_doctor_report.json` and resolve every `blocking:` unknown in `.ai/project_profile.yaml`. Doctor reports facts only; it does not auto-approve boundaries or generate `xcodebuild` commands.
3. **Coverage starts report-only when needed:** for legacy or broad source trees, keep `.ai/guards/coverage_policy.yaml` at `reportOnly: true` with narrowed include/exclude paths until boundaries are stable, then set `adoptionReviewed: true`. Android repositories should use this phase to map `app/src/main/**`, `*/src/main/**`, `app/src/test/**`, and `app/src/androidTest/**` before they tighten any flavor-specific associations.
4. **Staged CI:** start with **L1** governance only—full Git history plus `make check-ai-pr`. After L1 is stable, add **L2** `make ai-cockpit-quality` as a separate required job. For Android/Java, keep L2 non-blocking until the actual Gradle variant tasks and coverage boundaries are calibrated.
5. **Pilot Work Item:** run one governed task with quality optional if needed, then promote quality and Coverage to blocking gates.

For Java and Android repositories, treat the host JDK as a prerequisite before the flow above starts. The template does not install, switch, or manage JDK versions; confirm JDK 21 on the host first, then verify that `./gradlew` runs, then replace the preset task names with the actual variant-aware Gradle commands your project exposes.

The installed [Adoption Readiness](../../.ai/cockpit/adoption.md) checklist mirrors these steps for day-to-day use.

### Phase 4. Project Calibration

After committing the installation Adoption Work Item, create a second Work Item before calibration or configuration:

```sh
CONFIG_BASE="$(git rev-parse HEAD)"
make ai-start TASK=configure_ai_cockpit TITLE="Configure AI Cockpit for this project" MODE=code
```

Before editing configuration, update that Contract so its scope includes only the paths this project will change, typically:

```text
.ai/project_profile.proposed.yaml
.ai/project_profile.yaml
.ai/guards/**
Makefile.ai.stack
.github/workflows/**
.gitlab-ci.yml
```

Include `.gitlab-ci.yml` when the repository uses GitLab CI; include `.github/workflows/**` when it uses GitHub Actions. A single configure Work Item may cover both if your project changes both, but scope only paths you will actually edit.

Also replace skeleton unknowns, capability, execution decision, acceptance, and guideline fields before the `before_edit` checkpoint. The second Contract owns all Project Profile, Guard, quality-command, and CI changes; the archived installation Contract does not.

Do not treat `make ai-onboard` as an unattended acceptance step. The generated proposal and the stack preset both require human review, especially `target/ai_project_doctor_report.json`, `.ai/project_profile.proposed.yaml`, `Makefile.ai.stack`, and any `blocking:` unknowns that the calibration step surfaces.

Then calibrate the runtime before starting normal development:

```sh
make ai-onboard
# Or step by step:
make cockpit-doctor
make cockpit-calibrate
# Review the proposal, then explicitly create and edit the project-owned confirmation.
cp .ai/project_profile.proposed.yaml .ai/project_profile.yaml
${EDITOR:-vi} .ai/project_profile.yaml
# Set approval.reviewed: true only after confirming facts, boundaries, and unknowns.
make check-ai-project-profile
make check-ai-guard-calibration
make ai-cockpit-quality
make check-ai-adoption-ready
make ai-finish TASK=configure_ai_cockpit
git add .
git commit -m "configure AI Cockpit for this project"
make check-ai-pr AI_BASE_COMMIT="$CONFIG_BASE"
```

`cockpit-doctor` runs the existing environment checks and writes a read-only project-fact report to `target/ai_project_doctor_report.json`. `cockpit-calibrate` consumes that report and creates `.ai/project_profile.proposed.yaml`; it refuses to overwrite an existing proposal and never modifies Guard files. Human confirmation creates `.ai/project_profile.yaml` with explicit `approvedBoundaries` and approval metadata. Keep unresolved decisions in `unknowns`; entries prefixed with `blocking:` prevent readiness. For Android/Java, the main calibration question is not whether the preset exists, but whether the repo's module, flavor, and variant commands match the host Gradle wrapper.

### Phase 5. Validation

Before enabling production-required gates, complete the installed `.ai/cockpit/adoption.md` checklist and run the static configuration completeness gate:

```sh
make ai-cockpit-quality
make check-ai-adoption-ready
```

The readiness check fails closed until the confirmed Project Profile is valid, blocking unknowns are resolved, approved boundaries match Guards, all project quality commands are non-placeholder and nontrivial values, `.ai/guards/coverage_policy.yaml` records `adoptionReviewed: true`, and CI invokes the public release quality target recorded in `release.json` together with `check-ai-pr`. It cannot determine whether arbitrary commands provide meaningful project validation. Require those CI jobs to succeed before treating adoption as production-ready.

After adoption and calibration, a quick verify should show both readiness and status are clean:

```sh
make ai-cockpit-quality
make check-ai-status
make check-ai-status-consistency
```

If those commands succeed, the installation is operational rather than merely copied. `make check-ai-status` should show that no active adoption Work Item remains, and `make check-ai-status-consistency` should confirm the generated status matches the Work Item records.

<!-- public-quality-target: ai-cockpit-quality -->

## Reference Pages

- [Documentation Architecture](../reference/documentation-architecture.md)
- [Upgrade](../reference/upgrade.md)
- [Distribution](../reference/distribution.md)
- [Troubleshooting](../reference/troubleshooting.md)

### Phase 6. First Work Item

Continue in [First Work Item](first-work-item.md) for the full walkthrough that starts, checkpoints, and finishes the first governed task.

Installation is complete when validation succeeds and the first Work Item walkthrough succeeds.

## Upgrade

The installed `.ai/cockpit/version.json` records the distribution and Contract schema version. Use `--upgrade` for an existing installation:

```sh
CURRENT_VERSION=v0.5.16
TARGET_VERSION='<release-tag-newer-than-current>'
test "$TARGET_VERSION" != "$CURRENT_VERSION"
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL "https://raw.githubusercontent.com/xinglun/ai-cockpit-template/$TARGET_VERSION/install.sh" -o "$INSTALLER"
AI_COCKPIT_TEMPLATE_REF="$TARGET_VERSION" \
  sh "$INSTALLER" --upgrade --stack rust
```

The installer rejects distribution or Contract-schema downgrades; never set `TARGET_VERSION` lower than the version recorded in the installed `.ai/cockpit/version.json`.

By default, upgrade stops before writing if `.ai/work-items/active/` contains Work Item JSON. Finish and archive the active task first. `--upgrade-with-active` is an explicit high-risk override for recovery scenarios where changing governance semantics during a task is intentional.

Before replacement, managed files are copied under `.ai/cockpit/upgrade-backups/<timestamp>/`. Despite the historical directory name, the installer also uses it as a transaction rollback area when a first installation appends to an existing file such as `Makefile`; its presence does not mean an upgrade occurred. This directory and active review records are added to the managed `.gitignore` rules. Agent sections between the AI Cockpit markers are replaced as one managed block. If an existing `AGENTS.md`, `GEMINI.md`, or `CLAUDE.md` has no markers, upgrade preserves its content and appends the managed section. Customized guards and `checks.yaml` are backed up before the source version is installed. Project-owned `.ai/glossary.md` is preserved by default; `--replace-glossary` backs it up before installing a fresh template. The installer validates version metadata before writing, rejects distribution or Contract-schema downgrades, validates the installed managed runtime afterward, and automatically restores backed-up files if installation or post-copy validation fails. Review and remove successful-upgrade backups when they are no longer needed. `--force` replaces managed files without an upgrade backup, but does not replace the glossary unless explicitly requested.

If you did not use `--update-makefile`, add this line to your project Makefile:

```make
include Makefile.ai
```

After successful Work Item finish/archive, configure pull-request CI to fetch full Git history and run:

```sh
make check-ai-pr AI_BASE_COMMIT="$(git merge-base HEAD origin/main)"
```

For GitHub Actions, a complete minimal job is:

```yaml
jobs:
  ai-governance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - run: make check-ai-pr AI_BASE_COMMIT="$(git merge-base HEAD origin/${{ github.base_ref }})"
      # L2: add after L1 check-ai-pr is stable
      - run: make ai-cockpit-quality
```

For GitLab CI, fetch full history (`GIT_DEPTH: 0`) and start with L1 governance only:

```yaml
variables:
  GIT_DEPTH: "0"

ai-governance:
  stage: test
  script:
    - make check-ai-pr AI_BASE_COMMIT="$(git merge-base HEAD origin/${CI_DEFAULT_BRANCH})"
    # L2: uncomment after L1 is stable
    # - make ai-cockpit-quality
```

The PR check requires at least one archive Contract/Summary pair in the PR diff and validates every changed pair against the complete merge-base diff.

## Runtime Requirements

- Python 3.10 or newer.
- A Git repository with at least one commit, plus merge-base and three-dot diff support.
- POSIX shell and GNU Make-compatible command behavior.
- Linux and macOS are the supported CI/runtime environments. Native Windows shells are not currently supported; use WSL or another POSIX environment.

AI Cockpit is application-language-agnostic: its governance runtime does not depend on the target application's programming language. It is not runtime- or platform-agnostic; the Python, Make, POSIX, and Git requirements above remain mandatory, and stack/framework presets require project-specific configuration.
