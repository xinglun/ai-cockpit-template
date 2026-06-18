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
| Backtrack Guard | 默认阻止删除受保护的测试、snapshot 或 Work Item 记录。 |
| Coverage Guard | 默认阻止没有对应测试变更的已配置生产代码修改。 |
| Agent Risk Guard | 针对「prompt 仅是建议」、「mid-task 漂移」和「过度声明」风险的硬门控。 |
| AI Review Policy | 标记需要在 Change Summary 中明确说明 review 重点的治理和 CI 变更（仅报告）。 |
| Checkpoint | Mid-task 完整性快照，用于在完成前检测 scope 漂移。 |
| Status Consistency Guard | 验证 Cockpit 状态与当前 active Work Item 集合是否一致。 |
| Change Summary | 记录改了什么、验证了什么、还剩什么风险。 |
| Cockpit Status | 用一个生成视图展示当前 AI 任务状态。 |
| Finish Flow | 只有检查通过后才归档 Work Item。 |

## 信任模型

- `ai-start` 记录 `baseCommit` 和任务开始前脏文件的内容指纹。
- Contract v2 只能引用 `.ai/cockpit/checks.yaml` 中注册的 check ID，不能提供任意命令。
- `ai-finish` 记录 check ID、退出码、执行 commit、Contract hash、command hash 和脱敏输出摘要；这些是结构化记录，不是密码学证明。
- 安装器会分发相同的 PR validator 和 Make target。归档 Work Item 后，CI 运行 `make check-ai-pr AI_BASE_COMMIT=<merge-base>`。
- 每个非豁免 PR 路径必须由同一对 Contract/Summary 同时声明 scope 和 `changedFiles`。
- restricted/destructive approval 是 Contract 内的自声明流程记录；可信人工批准应由 CODEOWNERS、受保护 CI environment 或平台身份事件提供。
- AI Cockpit 用于减少误操作和流程漂移，不是针对恶意代理的安全沙箱。项目测试或 `make quality` 必须作为独立 required CI check 运行。

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

## 运行环境要求

- Python 3.10 或更高版本。
- 具有 merge-base 和 three-dot 差分（`...`）支持的 Git 环境。
- 兼容 POSIX shell 和 GNU Make 的命令执行环境。
- 官方支持 Linux 和 macOS 运行和 CI。原生 Windows shell 暂不支持，请在 WSL (Windows Subsystem for Linux) 或其他 POSIX 终端中运行。

## 版本与迁移策略

- **Contract v2 升级**：本项目在 `contractVersion: 2` 起引入了严格的 Check ID 映射机制以防注入风险。
- **历史归档兼容 (v1 Archive)**：在 `.ai/work-items/archive/` 中的历史 `v1` Contract 记录以只读方式被保留和兼容，但全新创建的任务必须强制使用 `v2` 格式，以确保管控契约和验证强度的升级。

## 进阶文档

- [安装](docs/installation.md)
- [概念导读（日文）](docs/overview.ja.md)
- [字段说明手册](docs/contract-fields.md)
- [配置](docs/configuration.md)
- [架构](docs/architecture.md)
- [设计思想](docs/design-philosophy.md)
- [案例：AI rollback corruption](docs/case-study-ai-rollback-corruption.md)
- [传播文案](docs/launch.md)
- [GitHub topics 建议](docs/topics.md)
- [语言 examples](examples/)
