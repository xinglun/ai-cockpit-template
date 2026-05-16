---
author: AI Cockpit Template contributors
description: 面向 Codex、Gemini、Antigravity 和其他 AI 编码代理的语言无关 AI 治理模板。
keywords:
  - ai-agents
  - codex
  - gemini
  - antigravity
  - agentic-coding
  - developer-tools
  - governance
  - template
  - automation
  - ci
---

# ai-cockpit-template

[English](README.md) | [日本語](README.ja.md)

`ai-cockpit-template` 是一个语言无关的 AI 治理脚手架，适用于使用 Codex、Gemini、Antigravity 或其他编码代理的工程团队。它为 AI 辅助代码修改增加一个可重复执行的 cockpit：先定义任务边界，再约束代理只能在范围内修改，要求验证，记录变更摘要，并保留审计轨迹。

## 面向谁

- 正在生产代码库中引入 AI 编码代理的团队。
- 希望 AI 生成的 diff 有边界、可审查、可回滚的维护者。
- 需要在 Rust、Flutter、TypeScript、Python 或混合语言代码库中使用同一套 AI 工作流的工程师。
- 希望轻量治理，但不想引入服务、数据库或专有运行时的组织。

## 解决什么问题

AI 代理执行速度很快，但也容易偏离任务范围、删除测试、重写无关文件、跳过验证，或者让 reviewer 无法判断到底改了什么。本模板把每个 AI 任务变成一个明确的 Work Item，并提供可机器检查的 scope、required checks 和最终 summary。

## 设计思想

人类文明不断建立系统，让系统进化，然后面对一个必然结果：系统复杂度逐渐超出人的直接掌控。到这个阶段，复杂度必须被压缩：内部过程成为 black box，而 cockpit 把人需要采取行动的状态反馈回来。

这个框架是为当前 AI 开发问题设计出来的。发想本身并不新，也不是照搬航空系统。只是当我们认真解决同一个控制问题时，最后自然会得到相似的形状。

强系统一定会被控制：计划、边界、验证、记录、状态显示。AI 开发同样需要这些层：

| AI 开发问题 | 需要的控制层 | 航空系统类比 |
| --- | --- | --- |
| 作业计划模糊 | Work Item Contract | 飞行计划 |
| 修改范围不明 | Scope Guard | 管制区域 |
| 验证不充分 | Required checks | 仪表确认 |
| 记录没有留下 | Change Summary 和 archive | 黑匣子 |
| 当前状态不可见 | Cockpit Status | 驾驶舱 |

所以最终结构自然接近航空控制系统：不是因为引入了外部形式，而是因为底层问题相同。

## 提供什么

- Work Item Contract：AI 修改文件前的任务边界。
- Scope Guard：阻止超出声明范围的修改。
- Backtrack Guard：报告未声明的测试、snapshot 或 Work Item 记录删除。
- Coverage Guard：报告没有对应测试变更的生产代码修改。
- Change Summary：记录改了什么、验证了什么、还剩什么风险。
- Cockpit Status：生成一屏可见的当前 AI 任务状态。
- Finish Flow：只有检查通过后才归档 Work Item。
- Installer：把 AI Cockpit 非破坏式安装到已有代码库。

## 目录结构

```text
.ai/
  cockpit/
    README.md
    checks.yaml
    current_status.md
  guards/
    backtrack_policy.yaml
    cockpit_status_policy.yaml
    coverage_policy.yaml
    file_boundary.yaml
    file_ownership.yaml
    scope_policy.yaml
    summary_policy.yaml
  work-items/
    _templates/
      work_item_contract.example.json
      work_item_summary.example.json
    active/
    archive/
examples/
  flutter/
  rust/
  typescript/
scripts/
  ai_*.py
  install_ai_cockpit.py
templates/
  make/
    Makefile.ai
  stacks/
    flutter.mk
    generic.mk
    python.mk
    rust.mk
    typescript.mk
install.sh
Makefile
AGENTS.md
GEMINI.md
```

## 快速开始

可以把本仓库作为 GitHub template 创建新项目，也可以安装到已有项目。

### 安装到已有项目

从本地 clone 安装：

```sh
/path/to/ai-cockpit-template/install.sh --stack rust
```

远程一键安装：

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

更安全的两步安装：

```sh
curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh -o install-ai-cockpit.sh
sh install-ai-cockpit.sh --stack rust
```

支持的 stack preset：

```text
generic
rust
flutter
typescript
python
```

安装器选项：

```text
--dry-run          只展示将执行的操作，不写文件。
--force            覆盖已有 AI Cockpit 文件。
--with-examples    把 examples/ 复制到目标代码库。
--update-makefile  向目标 Makefile 追加 "include Makefile.ai"。
```

默认安装是保守的：

- 写入 `Makefile.ai` 和 `Makefile.ai.stack`，不直接改已有 Makefile。
- 对已有 `AGENTS.md` 和 `GEMINI.md` 追加 AI Cockpit section。
- 已存在的文件默认跳过，除非使用 `--force`。

如果没有使用 `--update-makefile`，请在项目 Makefile 中加入：

```make
include Makefile.ai
```

### 创建 Work Item

创建 Work Item：

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

编辑生成的 Contract：

```text
.ai/work-items/active/example_change.contract.json
```

只在 Contract 声明的 `scope` 内修改代码或文档。

更新 Summary：

```text
.ai/work-items/active/example_change.summary.json
```

执行 finish flow：

```sh
make ai-finish TASK=example_change
```

Finish flow 会运行 AI 检查，生成 `.ai/cockpit/current_status.md`，检查状态，运行项目质量检查，并在通过后归档 Contract 和 Summary。

## 自定义项目检查

安装器会写入 `Makefile.ai.stack`。Stack preset 通过这些变量配置命令：

```make
PROJECT_FORMAT_CHECK = printf '%s\n' 'No formatter configured.'
PROJECT_TEST = printf '%s\n' 'No test command configured.'
PROJECT_LINT = printf '%s\n' 'No linter configured.'
```

Rust：

```make
PROJECT_FORMAT_CHECK = cargo fmt --all -- --check
PROJECT_TEST = cargo test
PROJECT_LINT = cargo clippy --all-targets -- -D warnings
```

Flutter：

```make
PROJECT_FORMAT_CHECK = dart format --set-exit-if-changed .
PROJECT_TEST = flutter test
PROJECT_LINT = flutter analyze
```

TypeScript：

```make
PROJECT_FORMAT_CHECK = npm run format:check
PROJECT_TEST = npm test
PROJECT_LINT = npm run lint
```

Python：

```make
PROJECT_FORMAT_CHECK = python3 -m ruff format --check .
PROJECT_TEST = python3 -m pytest
PROJECT_LINT = python3 -m ruff check .
```

也可以更新 `.ai/cockpit/checks.yaml`，让代理知道每个任务应该选择哪些检查。

## Guard 配置

- `.ai/guards/file_ownership.yaml` 控制 restricted / forbidden AI 写入。
- `.ai/guards/file_boundary.yaml` 阻止 generated 和 runtime artifact 混入代码 diff。
- `.ai/guards/coverage_policy.yaml` 定义生产代码和测试路径 pattern。
- `.ai/guards/scope_policy.yaml` 定义 always allowed 路径和可选 dependency scope 规则。

Guard YAML 解析器只支持一个很小的 YAML 子集，因此脚本只依赖 Python 标准库。

## 版本化安装

使用 tag 可以获得可复现安装：

```sh
AI_COCKPIT_TEMPLATE_REF=v0.1.1 \
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

## 模板策略

不要把业务逻辑、个人路径、真实 API key、GitHub secret 或组织专属运行时配置加入本仓库。模板保持通用，真实项目策略放到采用该模板的代码库中。
