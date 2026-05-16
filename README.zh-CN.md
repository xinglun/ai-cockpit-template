---
author: Ray
title: "AI Cockpit"
description: 面向 Codex、Gemini、Claude、Cursor、Antigravity 和其他 AI 编码代理的语言无关 AI 治理模板。
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

[English](README.md) | [日本語](README.ja.md)

AI 编码代理可能会：

- 重写无关文件
- 悄悄删除测试
- 绕过验证
- 让 reviewer 猜不出发生了什么

你的 AI agent 不应该拥有整个仓库的 root access。

AI Cockpit 是面向 coding agents 的 AI Change Governance。

它为 AI 辅助开发增加一套轻量 AI review workflow。

![AI Cockpit demo](docs/assets/ai-cockpit-demo.gif)

**AI 改了 37 个文件。Cockpit 阻止了 merge。**

AI Cockpit 让 AI 生成的变更有边界、可审查、可审计。

我反复看到 AI 重写无关文件、回退已完成工作、绕过 review 预期。所以我做了一套围绕 scope、checks、summary 和 status 的轻量 change-control workflow。

## 30 秒理解

Before：

```text
AI 改了 24 个文件。
没人知道为什么。
测试可能已经消失。
Review 从混乱开始。
```

After：

```text
任务范围已声明。
检查被强制执行。
Summary 已生成。
Cockpit 已更新。
Review 从上下文开始。
```

## 3 分钟安装

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

启动一个受治理的 AI 任务：

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

带检查和审计记录完成它：

```sh
make ai-finish TASK=example_change
```

## 工作方式

```text
Plan -> Scope -> Verify -> Summarize -> Status -> Archive
```

| 层 | 作用 |
| --- | --- |
| Work Item Contract | 在 AI 修改文件前声明任务边界。 |
| Scope Guard | 阻止超出声明 scope 的变更。 |
| Backtrack Guard | 报告未声明删除测试、snapshot 或 Work Item 记录。 |
| Coverage Guard | 报告没有对应测试变更的生产代码修改。 |
| Change Summary | 记录改了什么、验证了什么、还剩什么风险。 |
| Cockpit Status | 用一个生成视图展示当前 AI 任务状态。 |
| Finish Flow | 只有检查通过后才归档 Work Item。 |

## 它会拦住什么

```text
[BLOCKED]
Scope violation detected.

Unauthorized file modification:
- src/auth/payment.rs

Allowed scope:
- src/auth/session.rs
- tests/auth/session_test.rs
```

## 支持

代理：

```text
Codex, Gemini, Claude, Cursor, Antigravity, and other coding agents
```

技术栈：

```text
generic, rust, flutter, typescript, python, go, java, kotlin, swift, ruby, php, csharp
```

## 进阶文档

- [安装](docs/installation.md)
- [配置](docs/configuration.md)
- [架构](docs/architecture.md)
- [设计思想](docs/design-philosophy.md)
- [案例：AI rollback corruption](docs/case-study-ai-rollback-corruption.md)
- [传播文案](docs/launch.md)
- [GitHub topics 建议](docs/topics.md)
- [语言 examples](examples/)
