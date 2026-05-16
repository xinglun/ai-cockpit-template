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

Install AI Cockpit into an existing repository:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

Start a governed AI task:

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

Edit the generated Contract:

```text
.ai/work-items/active/example_change.contract.json
```

Update the Summary before finishing:

```text
.ai/work-items/active/example_change.summary.json
```

Run the finish flow:

```sh
make ai-finish TASK=example_change
```

## Local Install

From a local clone:

```sh
/path/to/ai-cockpit-template/install.sh --stack rust
```

## Safer Two-Step Install

```sh
curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh -o install-ai-cockpit.sh
sh install-ai-cockpit.sh --stack rust
```

## Versioned Install

Use a tag for reproducible installs:

```sh
AI_COCKPIT_TEMPLATE_REF=v0.2.0 \
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

## Options

```text
--dry-run          Show actions without writing files.
--force            Overwrite existing AI Cockpit files.
--with-examples    Copy examples/ into the target repository.
--update-makefile  Append "include Makefile.ai" to the target Makefile.
```

By default, the installer is conservative:

- It writes `Makefile.ai` and `Makefile.ai.stack` instead of modifying an existing Makefile.
- It appends AI Cockpit sections to existing `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md`.
- It installs Cursor rules under `.cursor/rules/ai-cockpit.mdc`.
- It skips existing files unless `--force` is provided.

If you did not use `--update-makefile`, add this line to your project Makefile:

```make
include Makefile.ai
```

