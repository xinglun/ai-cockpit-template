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

日本語の主要入口は、[日本語 README](../../README.ja.md)、[インストール](../getting-started/installation.ja.md)、[最初の Work Item](../getting-started/first-work-item.ja.md)、[設定](../configuration.ja.md)、[アーキテクチャ](../architecture.ja.md) です。詳細な英語リファレンスへ進む必要がある場合は、各日本語ページの対応リンクを使用してください。

## Authoritative entry points

| Need | Authoritative page |
| --- | --- |
| Runtime/component facts | [Architecture](../architecture.md) |
| Contract and Summary field semantics | [Contract Fields](../contract-fields.md) |
| Reviewer interpretation of generated state | [How to Read Cockpit Status](how-to-read-cockpit-status.md) |
| Agent execution and lifecycle rules | [Cockpit runtime guide](../../.ai/cockpit/README.md) |

The README files are short five-minute positioning and entry points. They do not carry the complete feature catalogue or Release Reference. The authoritative pages below assign detailed philosophy, architecture, field semantics, status interpretation, and execution rules to their respective layers.

This page describes the stable documentation split for AI Cockpit. It keeps the guided adoption flow short, moves support material into reference pages, and gives the README a clear entry path for first-time readers.

## Page Roles

| Page | Role | Reader question |
| --- | --- | --- |
| [README.md](../../README.md) | Entry page | What is this, and how do I start quickly? |
| [docs/getting-started/installation.md](../getting-started/installation.md) | Getting started | How do I install and adopt AI Cockpit? |
| [docs/getting-started/first-work-item.md](../getting-started/first-work-item.md) | Getting started | How do I start the first governed task? |
| [docs/philosophy/design-philosophy.md](../philosophy/design-philosophy.md) | Philosophy | Why does AI Cockpit exist, and how does it calibrate trust? |
| [docs/architecture.md](../architecture.md) | Architecture | How does the governance evidence flow work? |
| Reference pages | Reference | Where are field, policy, installation, distribution, and troubleshooting details? |
| [docs/configuration.md](../configuration.md) | Configuration reference | Which stack presets and guard settings should I calibrate? |
| [docs/reference/upgrade.md](upgrade.md) | Upgrade guide | How do I move an existing installation forward? |
| [docs/reference/distribution.md](distribution.md) | Distribution reference | What installer options and published integrity capabilities exist? |
| [docs/reference/troubleshooting.md](troubleshooting.md) | Recovery guide | What failed, and how do I recover? |
| [docs/installation.md](../installation.md) | Compatibility entry | Where do old installation links land now? |
| [docs/upgrade.md](../upgrade.md) | Compatibility entry | Where do old upgrade links land now? |
| [docs/distribution.md](../distribution.md) | Compatibility entry | Where do old distribution links land now? |
| [docs/troubleshooting.md](../troubleshooting.md) | Compatibility entry | Where do old troubleshooting links land now? |
| [docs/design-philosophy.md](../design-philosophy.md) | Compatibility entry | Where do old philosophy links land now? |

## Split Rules

- Keep the README short enough that a reader can reach the installer in one glance.
- Use README for five-minute positioning, the shortest governance loop, and the Quick Install entry; do not turn it into a complete feature catalogue or Release Reference.
- Keep `docs/getting-started/installation.md` focused on the adoption lifecycle and validation.
- Keep `docs/getting-started/first-work-item.md` focused on the first governed task.
- Keep Philosophy authoritative for why AI Cockpit exists and how calibrated trust, evidence, and responsibility boundaries shape the design.
- Keep Architecture authoritative for repository governance flow, component boundaries, and the Native/Delegated Evidence split.
- Keep Reference pages authoritative for fields, policies, installation, distribution, and troubleshooting.
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
