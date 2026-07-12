---
author: Ray
title: "Documentation Architecture"
description: Documentation information architecture for AI Cockpit.
keywords:
  - ai-cockpit
  - documentation
  - information-architecture
  - quick-start
  - reference
---

# Documentation Architecture

## Authoritative entry points

| Need | Authoritative page |
| --- | --- |
| Runtime/component facts | [Architecture](../architecture.md) |
| Contract and Summary field semantics | [Contract Fields](../contract-fields.md) |
| Reviewer interpretation of generated state | [How to Read Cockpit Status](how-to-read-cockpit-status.md) |
| Agent execution and lifecycle rules | [Cockpit runtime guide](../../.ai/cockpit/README.md) |

The README files are entry points; these pages define the architecture facts, field semantics, status interpretation, and execution rules respectively.

This page describes the stable documentation split for AI Cockpit. It keeps the guided adoption flow short, moves support material into reference pages, and gives the README a clear entry path for first-time readers.

## Page Roles

| Page | Role | Reader question |
| --- | --- | --- |
| [README.md](../../README.md) | Entry page | What is this, and how do I start quickly? |
| [docs/getting-started/installation.md](../getting-started/installation.md) | Getting started | How do I install and adopt AI Cockpit? |
| [docs/getting-started/first-work-item.md](../getting-started/first-work-item.md) | Getting started | How do I start the first governed task? |
| [docs/configuration.md](../configuration.md) | Configuration reference | Which stack presets and guard settings should I calibrate? |
| [docs/reference/upgrade.md](upgrade.md) | Upgrade guide | How do I move an existing installation forward? |
| [docs/reference/distribution.md](distribution.md) | Distribution reference | What installer options and published integrity capabilities exist? |
| [docs/reference/troubleshooting.md](troubleshooting.md) | Recovery guide | What failed, and how do I recover? |
| [docs/philosophy/design-philosophy.md](../philosophy/design-philosophy.md) | Philosophy | Why is the system shaped this way? |
| [docs/installation.md](../installation.md) | Compatibility entry | Where do old installation links land now? |
| [docs/upgrade.md](../upgrade.md) | Compatibility entry | Where do old upgrade links land now? |
| [docs/distribution.md](../distribution.md) | Compatibility entry | Where do old distribution links land now? |
| [docs/troubleshooting.md](../troubleshooting.md) | Compatibility entry | Where do old troubleshooting links land now? |
| [docs/design-philosophy.md](../design-philosophy.md) | Compatibility entry | Where do old philosophy links land now? |

## Split Rules

- Keep the README short enough that a reader can reach the installer in one glance.
- Keep `docs/getting-started/installation.md` focused on the adoption lifecycle and validation.
- Keep `docs/getting-started/first-work-item.md` focused on the first governed task.
- Move upgrade, distribution, and recovery details into their own reference pages.
- Keep stack and guard specifics in `docs/configuration.md`, where they can be reused by the install guide without duplicating the full reference.
- Preserve version-neutral guidance where possible, and keep release-specific notes out of the main installation flow.
- Use compatibility entry pages when an older path must continue to resolve.

## Intended Navigation

1. Start in [README.md](../../README.md) for the Quick Install entry.
2. Open [docs/getting-started/installation.md](../getting-started/installation.md) for the guided installation and adoption path.
3. Open [docs/getting-started/first-work-item.md](../getting-started/first-work-item.md) when you are ready to start the first governed task.
4. Use [docs/configuration.md](../configuration.md) when you need stack or guard calibration detail.
5. Use [docs/reference/upgrade.md](upgrade.md), [docs/reference/distribution.md](distribution.md), and [docs/reference/troubleshooting.md](troubleshooting.md) as reference pages.
6. Use [docs/philosophy/design-philosophy.md](../philosophy/design-philosophy.md) for the design rationale.

This page is the navigation map for the documentation system. It explains how the documentation is organized so future edits can stay in the right layer.
