---
author: Ray
title: "AI Cockpit"
description: 面向 Codex、Gemini、Claude、Cursor、Antigravity 等 AI 编码代理、与目标应用语言无关的协作式工程环境与变更治理模板。
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

不应在缺少边界明确、独立执行的 review 时接受 AI 生成的变更。

AI Cockpit 是写入后的差分治理流程，不是文件系统权限边界或安全沙箱。

AI Cockpit 是面向 agentic development 的协作式工程环境。

它通过显式 scope、委派式 checks、review 证据和可审计的任务记录来提供 AI Change Governance。

![AI Cockpit demo](docs/assets/ai-cockpit-demo.gif)

**AI 改了 37 个文件。Cockpit 阻止了 merge。**

AI Cockpit 让 AI 生成的变更有边界、可审查、可审计。

我反复看到 AI 重写无关文件、回退已完成工作、绕过 review 预期。所以我围绕 scope、checks、summary 和 status 设计了一套协作式工程环境，而治理是其中的核心控制机制。

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

<!-- install-prerequisites: python3.10,git-initial-commit,curl,gnu-make,posix -->

**前置条件：**支持 POSIX shell 的 Linux、macOS 或 WSL；Python 3.10+；Git、curl 和 GNU Make；以及至少已有一个提交且工作树干净的 Git 仓库。所选 stack 的 formatter、测试运行器、SDK 和构建插件也必须预先安装。

## 安装最新公开运行时

```sh
ADOPTION_BASE="$(git rev-parse HEAD)"
STACK="${STACK:-generic}" # generic、python、go、rust、typescript、java、android、kotlin、flutter、swift、ruby、php 或 csharp
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

该命令优先读取公开的 `release.json`；在发布元数据尚未上线的过渡期，则从公开的语义化版本标签中选择最高版本。随后只下载并执行解析出的固定标签安装器。公开版本的能力可能落后于源码树；创建首次采用 PR 前请先阅读[安装文档](docs/installation.md)。

先审阅并扩展生成的配置 Contract scope，再修改 Project Profile、Guard、质量命令和 CI。然后在启用阻断型门禁前，根据目标工程校准治理运行时：

<!-- governance-flow: install,configure-work-item,onboard,doctor,calibrate,confirm,validate,readiness,develop -->

```sh
make ai-onboard
# 或分步执行:
make cockpit-doctor
make cockpit-calibrate
# 审阅 .ai/project_profile.proposed.yaml，再创建并批准 .ai/project_profile.yaml。
make check-ai-project-profile
make check-ai-guard-calibration
make check-ai-adoption-ready
make ai-finish TASK=configure_ai_cockpit
git add .
git commit -m "configure AI Cockpit for this project"
make check-ai-pr AI_BASE_COMMIT="$CONFIG_BASE"
```

Doctor 不修改项目策略，只记录检测事实、证据、置信度、建议和 unknown。Calibration 只生成候选文件，不覆盖 Guard，也不自动批准高风险路径。人工明确确认且 Readiness 检查通过后，再启动受治理的 AI 任务：

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
| Scope Guard | 检测超出声明 scope 的变更，并阻止完成、归档或合并门禁通过。 |
| Backtrack Guard | 检测受保护测试、snapshot 或 Work Item 记录的删除，并阻止已配置门禁通过。 |
| Coverage Guard | 要求每个生产代码路径都有由项目关联规则匹配的测试路径变更；它不分析测试内容，也不证明运行时覆盖率。 |
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
- AI Cockpit 用于减少误操作和流程漂移，不是针对恶意代理的安全沙箱。对于上述命令选择的公开版本，项目测试或 `make ai-cockpit-quality` 必须作为独立 required CI check 运行。

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
generic, rust, flutter, typescript, python, go, java, android, kotlin, swift, ruby, php, csharp
```

兼容性等级：

<!-- stack-tiers: verified=python,go,rust,typescript,java,kotlin,ruby,php,csharp,flutter,android,swift; workflow-implemented=; preset-only=generic -->

- **Hosted CI 已验证：** `python`、`go`、`rust`、`typescript` 在 `real-stack-quality` 中运行；`java`、`kotlin`、`ruby`、`php`、`csharp` 在 `extended-real-stack-quality` 中运行；`flutter`、`android`、`swift` 在 `mobile-stack-quality` 中对最小工程执行 `make ai-cockpit-quality`。
- **仅预设：** `generic` 在完成配置前会按设计失败关闭。
- **不支持的运行环境：** 原生 Windows shell。请使用 WSL 或其他 POSIX 环境。

技术栈预设是可按项目修改的起点，不负责安装依赖。目标项目必须已具备 formatter、测试运行器、SDK 和构建插件；例如 Java 和 Android 预设要求 Gradle Wrapper 与 Spotless 配置，Python 预设要求 Ruff 和 pytest。`examples/` 仅覆盖部分技术栈，目前并未包含每一种预设。

治理运行时本身不依赖目标语言，但技术栈预设和默认 guard 路径并不代表完整的框架支持。将其设为 CI 必需检查前，必须根据目标仓库调整 `Makefile.ai.stack` 和 `.ai/guards/coverage_policy.yaml`。

安装只完成治理运行时部署，并不代表生产适配完成。Project Profile、Guard、质量命令和 CI 适配由独立的 `configure_ai_cockpit` Work Item 覆盖。Adoption Readiness 还要求已批准的 Project Profile、Profile 与 Guard 一致、质量命令非占位、Coverage 路径已确认，并在 CI 中配置 `ai-cockpit-quality` 和 `check-ai-pr`。该检查只验证静态完整性，不是安全证明，也不能证明项目命令本身有效。

<!-- release-capabilities: auditable-adoption,sha256-verification -->
<!-- public-quality-target: ai-cockpit-quality -->

当前公开版本已经包含可审计的首次采用流程，以及调用方提供 SHA256 时的校验能力。项目质量命令、Coverage 路径和 CI 仍需针对目标工程明确适配。

## 运行环境要求

- Python 3.10 或更高版本。
- 具有 merge-base 和 three-dot 差分（`...`）支持的 Git 环境。
- 兼容 POSIX shell 和 GNU Make 的命令执行环境。
- 官方支持 Linux 和 macOS 运行和 CI。原生 Windows shell 暂不支持，请在 WSL (Windows Subsystem for Linux) 或其他 POSIX 终端中运行。

仓库的 `make quality` 会运行全部测试，要求脚本总覆盖率不低于 60%，并对生命周期关键脚本设置分文件回归下限；同时对 `scripts/` 和 `tests/` 执行 Ruff，对全部治理脚本执行 Mypy，并执行中高等级 Bandit 扫描、Python 编译、差分检查和文档一致性检查。

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
