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

Install a fixed release of AI Cockpit into an existing repository:

```sh
VERSION=v0.5.14
STACK="${STACK:-generic}"
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL "https://raw.githubusercontent.com/xinglun/ai-cockpit-template/$VERSION/install.sh" -o "$INSTALLER"
AI_COCKPIT_TEMPLATE_REF="$VERSION" sh "$INSTALLER" --stack "$STACK" --update-makefile --create-adoption
```

Review release notes before changing `VERSION`. A branch such as `main` is mutable and is not recommended for reproducible installation. The temporary bootstrap is removed automatically when the shell exits.

Public `v0.5.14` includes the auditable adoption bootstrap. The first installation PR can generate its own bounded Contract/Summary pair and pass complete `check-ai-pr` ownership after the documented finish and commit steps.

## Auditable First Adoption

From a clean Git repository with at least one commit, run the fixed release command above, then finish the generated adoption Work Item:

```sh
make ai-finish TASK=adopt_ai_cockpit
git add .
git commit -m "adopt AI Cockpit governance"
make check-ai-pr AI_BASE_COMMIT='<pre-adoption-commit>'
```

The installer-generated Work Item owns every file actually written or appended by installation. It keeps project quality configuration as an explicit follow-up rather than recording generic placeholder commands as passed. `--create-adoption` fails before writing unless the repository has an initial commit, a clean worktree, and no active Work Item.

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

Also replace skeleton unknowns, capability, execution decision, acceptance, and guideline fields before the `before_edit` checkpoint. The second Contract owns all Project Profile, Guard, quality-command, and CI changes; the archived installation Contract does not.

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

`cockpit-doctor` runs the existing environment checks and writes a read-only project-fact report to `target/ai_project_doctor_report.json`. Each detected fact and suggested boundary includes evidence and confidence. Directory existence is evidence, not approval. `cockpit-calibrate` consumes that report and creates `.ai/project_profile.proposed.yaml`; it refuses to overwrite an existing proposal and never modifies Guard files.

Human confirmation creates `.ai/project_profile.yaml` with explicit `approvedBoundaries` and approval metadata. Keep unresolved decisions in `unknowns`; entries prefixed with `blocking:` prevent readiness. `check-ai-guard-calibration` then verifies that approved production/test/generated/critical paths are represented by Coverage, boundary, ownership, or review policies.

`ai-doctor` is advisory. Before enabling production-required gates, complete the installed `.ai/cockpit/adoption.md` checklist and run the static configuration completeness gate:

```sh
make ai-cockpit-quality
make check-ai-adoption-ready
```

The readiness check fails closed until the confirmed Project Profile is valid, blocking unknowns are resolved, approved boundaries match Guards, all project quality commands are non-placeholder and nontrivial values, `.ai/guards/coverage_policy.yaml` records `adoptionReviewed: true`, and CI invokes both the public release quality target (`ai-cockpit-quality` for v0.5.14) and `check-ai-pr`. It cannot determine whether arbitrary commands provide meaningful project validation. Require those CI jobs to succeed before treating adoption as production-ready.

This workflow is published in `v0.5.14`. Older tags do not gain adoption capability retroactively.

<!-- public-quality-target: ai-cockpit-quality -->

Start a governed AI task:

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

`ai-start` requires the target to be a Git repository with at least one commit so `baseCommit` can identify a trustworthy diff baseline. For a new repository, create and commit its initial files before running this command. The installer prints a warning when this prerequisite is not met.

Edit the generated Contract:

```text
.ai/work-items/active/example_change.contract.json
```

Before changing project files, replace the skeleton placeholders and confirm this minimum checklist:

- `scope` contains every file or path pattern the task may change, and `outOfScope` states explicit boundaries.
- `sources`, `acceptance`, and `verification` describe the evidence, done conditions, and registered checks.
- `unknowns` is empty, `notCodable` is `false`, and `executionDecision.status` is `continue`.
- `agentCapability.canImplement` and `agentCapability.canVerify` are `true`; human decisions remain explicit.
- Run `make ai-checkpoint STAGE=before_edit` before implementation.

Update the Summary before finishing:

```text
.ai/work-items/active/example_change.summary.json
```

Run the finish flow:

```sh
make ai-finish TASK=example_change
```

`ai-finish` runs the registered checks, updates the Summary with execution evidence, regenerates status, and archives the Contract/Summary pair. A successful walkthrough ends with no files under `.ai/work-items/active/`, an archive pair under `.ai/work-items/archive/<year>/`, and `make check-ai-status-consistency` passing.

## Local Install

From a local clone:

```sh
/path/to/ai-cockpit-template/install.sh --stack rust --update-makefile
```

## Published Integrity Capabilities

The documented release is defined in `release.json`. Public `v0.5.14` supports caller-provided `AI_COCKPIT_TEMPLATE_SHA256` verification and fails before extraction when the downloaded archive digest differs.

The project does not currently publish trusted archive checksum files, cryptographic signatures, or provenance attestations. Obtain the expected SHA256 through a trusted independent channel before setting `AI_COCKPIT_TEMPLATE_SHA256`; support for comparing a caller-provided digest is not itself a published integrity root. Worktree capabilities are not public until `release.json` points to a tag whose real installer passes `make check-release-distribution`.

## Options

```text
--dry-run          Show actions without writing files.
--force            Overwrite existing AI Cockpit files.
--upgrade          Back up and replace managed runtime, policy, and agent marker files.
--upgrade-with-active
                   Permit a high-risk upgrade while active Work Item JSON exists.
--replace-glossary Back up and explicitly replace the project-owned .ai/glossary.md.
--create-adoption Create the first auditable adoption Work Item; requires clean committed Git state.
--with-examples    Copy examples/ into the target repository.
--update-makefile  Append "include Makefile.ai" to the target Makefile.
```

Without `--update-makefile`, the installer does not modify the host `Makefile`; it writes separate `Makefile.ai` and `Makefile.ai.stack` files. The recommended command above does pass `--update-makefile`, so it appends `include Makefile.ai`. Public v0.5.14 validates reserved `ai-cockpit-*` targets before writing and exposes namespaced project-quality targets.

Other conservative defaults:

- Public v0.5.14 uses namespaced `ai-cockpit-*` recipes to avoid replacing common host targets.
- It appends AI Cockpit sections to existing `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md`.
- It installs Cursor rules under `.cursor/rules/ai-cockpit.mdc`.
- It skips existing files unless `--force` is provided.
- It creates clean active/archive directories and does not copy the template repository's Work Item history.
- It installs `templates/glossary.md` only when `.ai/glossary.md` is absent. Reinstall, `--force`, and `--upgrade` preserve a project glossary unless `--replace-glossary` is explicitly provided.

The installed runtime includes `scripts/ai_check_pr.py`, the `check-ai-pr` Make target, and Contract-aware guard wiring. The distribution template is exercised independently from the repository-root Makefile in CI.

Stack selection configures quality-command starting points. It does not infer the target repository's production and test directories. Review `.ai/guards/coverage_policy.yaml` during adoption and add the project's layouts before relying on Coverage Guard as a required gate.

## Common Failures and Recovery

- `No rule to make target 'ai-start'`: rerun the installer with `--update-makefile`, or add an active `include Makefile.ai` line to the project Makefile. A commented line is not active.
- Contract validation reports placeholders or unknowns: complete the checklist above; do not start implementation by weakening required checks.
- Status consistency fails: run `make repair-ai-status` only when there is no active item or exactly one paired Contract/Summary. Repair unpaired or multiple active records manually.
- A project quality command is missing: install/configure the selected stack tools or edit `Makefile.ai.stack`; the generic preset intentionally fails closed.
- An active task must be abandoned: preserve or document relevant evidence, then remove/archive the pair deliberately. Do not delete a single record from the pair.

## Upgrade

The installed `.ai/cockpit/version.json` records the distribution and Contract schema version. Use `--upgrade` for an existing installation:

```sh
CURRENT_VERSION=v0.5.14
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
      - run: make ai-cockpit-quality
```

The PR check requires at least one archive Contract/Summary pair in the PR diff and validates every changed pair against the complete merge-base diff.

## Runtime Requirements

- Python 3.10 or newer.
- A Git repository with at least one commit, plus merge-base and three-dot diff support.
- POSIX shell and GNU Make-compatible command behavior.
- Linux and macOS are the supported CI/runtime environments. Native Windows shells are not currently supported; use WSL or another POSIX environment.

AI Cockpit is application-language-agnostic: its governance runtime does not depend on the target application's programming language. It is not runtime- or platform-agnostic; the Python, Make, POSIX, and Git requirements above remain mandatory, and stack/framework presets require project-specific configuration.
