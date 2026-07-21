---
author: Ray
title: "2026-07-21 Bootstrap Adoption and Project-Calibrated Complexity Review Remediation"
description: "根据 Bootstrap Adoption 评审，把首次导入、项目校准和正式治理拆成串行、可审计的 Work Item 执行计划。"
keywords:
  - bootstrap-adoption
  - project-configuration
  - complexity-calibration
  - review-remediation
  - work-item-lifecycle
---

# 2026-07-21 Bootstrap Adoption 评审整改执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将对象工程首次导入 AI Cockpit 的流程收敛为 Bootstrap Adoption → Project Configuration → Governed Development 三阶段，并以对象工程自身基线校准复杂度、质量命令和 Guard。

**Architecture:** Bootstrap 只负责检测、提议、用户配置、最终确认、最小写入和运行时验证；合并后由 `configure_ai_cockpit` Work Item 完成 Project Doctor、Profile、Complexity Baseline、Policy Proposal、Human Confirmation 和 Adoption Readiness；只有 Ready 后才进入正式治理开发。所有阶段都以证据为准，不把模板仓库阈值、Agent 自报或未执行命令当作采用方事实。

**Tech Stack:** Python、pytest、Make、Git、JSON/YAML、Markdown，以及项目自身的质量工具和 PR 平台。

## Global Constraints

- Bootstrap 最终确认前不得写入对象 Repository，不得创建 `.ai/`、Branch、Worktree、Contract 或 Summary；Session 必须保存在 Repository 外部。
- 一个工单对应一个 Contract v2、一个专用分支、一个 PR；工单不得并行，不得跨工单共享分支。
- 每个工单必须从执行时最新远端默认分支创建，并记录 `baseRemote`、`baseBranch`、`baseCommit`。
- 每个工单必须完成完整闭环：Contract → Preflight → 实现/文档 → 验证 → Summary → `ai-finish`/归档 → 推送 → PR → 合并 → `ai-close-work-item` → 本地/远端分支清理 → 默认分支同步。
- 当前工单未得到 `ready for next Work Item` 前，不得创建、实现或合并下一个工单；失败留在当前工单修复。
- Evidence over Self-Declaration：缺失、过期、冲突、未绑定或 `not_run` 的证据不得被写成通过。
- AI Cockpit 仍是 Repository Governance Layer，不宣称是 Agent Runtime、Sandbox、可信身份系统、不可篡改审计系统或企业合规证明。
- 现有历史计划和归档证据默认保留；计划清理只能删除明确无引用、已被替代且具备审计记录的副本。

## 一、评审接收与总结

### 评审材料结论

评审材料确认，首次安装时对象工程不存在 Runtime、`.ai/`、`ai-start`、Contract、Preflight、Guard、Summary、Cockpit Status 和标准 Work Item 生命周期，因此不能直接套用模板仓库的治理阈值或正常开发流程。

本次整改必须建立三个明确阶段：

| 阶段 | 允许做什么 | 不得宣称什么 |
| --- | --- | --- |
| Bootstrap Adoption | 检测 Repository、收集配置、用户 Review/Confirm、最小写入、生成 Adoption Evidence、验证 Runtime | 不得批准治理策略，不得宣布 Adoption Ready |
| Project Configuration | `configure_ai_cockpit`、Doctor、Profile Proposal、复杂度基线、Policy Proposal、人工确认、Preflight 重验 | 不得把模板阈值直接复制为对象工程政策 |
| Governed Development | 使用对象工程已确认的 Profile、Quality Commands、Complexity Policy 和 Guards 执行标准 Work Item | 不得把结构化治理记录等同于身份、隔离、合规或不可篡改审计 |

### 必须落实的评审问题

- 安装向导必须先 Detect → Propose → User Configure → Review → Confirm → Revalidate → Bootstrap Write → Runtime Verification。
- Detected、Proposed、Required User Input 三类输入必须区分；不唯一或属于治理决策的内容不得静默猜测。
- Session 必须外置，支持 Back、Review、Cancel、Resume；上游输入变化必须使下游答案失效并重新确认。
- Dirty Tree、Remote、Default Branch、Bootstrap Base、Branch/Worktree、Stack、Makefile、文档语言、Write Scope 和下一阶段提示都必须有明确处理和证据。
- Bootstrap Write Scope 必须禁止业务代码、CI、复杂度策略和正式治理策略被意外修改。
- `configure_ai_cockpit` 必须建立 Adoption Baseline、Active Complexity Baseline 和 Work Item Base Commit，并区分历史、新增和恶化复杂度。
- 复杂度检查必须按对象工程校准；Unavailable 不等于 Allow，历史复杂度默认不因导入而ブロッキング，新复杂度和恶化复杂度才进入治理判断。
- Bootstrap、Configuration 和 Governed Development 的 CLI、状态、Smoke、文档和测试必须共享可机器读取的生命周期事实源。
- 多语言文档和跨技术栈证据必须保持事实一致；未执行的工具链必须明确 `not_run`。

## 二、已获授权与需要确认的事项

用户已授权本计划按以下方式连续执行，无需在每个工单开始前再次询问“是否允许修改或验证”：

- 修改实现代码、测试、Schema、Guard、治理配置、CI、示例和文档。
- 为每个工单从最新远端默认分支创建专用分支，创建/更新 Contract v2、Summary 和证据记录。
- 运行本地与 CI 检查，创建、推送、审查和合并每个工单的唯一 PR。
- 每个工单执行 `make ai-finish TASK=<task>`、归档、PR 合并后的 `make ai-close-work-item TASK=<task>`，并清理本地和远端分支。
- 全部整改后进行妄想/无证据声明测试；不通过则继续修改或创建单一修复工单，直到通过。
- 对齐现有文档、发布新版本，并在最后清理执行计划文档。

以下是执行期间仍必须向用户展示并取得具体决定的事项；上述授权表示这些确认请求已获准进入流程，不表示 Agent 可以替用户猜测答案：

- Bootstrap Review Summary 中的 Primary Remote、Default Branch、Bootstrap Base Ref、Installation Branch/Worktree、Dirty Tree 处理方式。
- Primary Stack、Makefile 集成方式、文档语言、Bootstrap Write Scope 和下一阶段提示偏好。
- `make ai-start` 或 `make ai-preflight` 报告 `needs_human_confirmation` / `not_ready` 时的 Human Decision；决定后必须重新计算 Contract/Preflight Hash。
- 真实 PR 编号、合并 SHA、发布 Tag、Workflow、Provider Asset、Digest、分支删除和默认分支同步结果；这些只能由实际证据填写。

## 三、每个工单必须执行的完整流程

以下流程适用于本计划全部工单，包括最后四个收尾工单。每个工单完成后，循环回到第 1 步执行下一个工单，直到列表全部完成；任何失败都停留在当前工单。

1. 获取远端默认分支最新提交，记录 `baseRemote`、`baseBranch`、`baseCommit` 和基线 Dirty Paths。
2. 从该基线创建唯一专用分支，运行 `make ai-start TASK=<task> TITLE="..." MODE=code`；计划作者工单可使用已建立的 `author_todo` Contract。
3. 读取 `.ai/cockpit/README.md`、`.ai/README.md`、`.ai/glossary.md` 和相关源文档；完成 Contract v2 的 Intent、scope、outOfScope、sources、unknowns、acceptance、scenarioCoverage、verification、risk 和 capability 字段。
4. 运行 `make ai-preflight`。若为 `needs_human_confirmation` 或 `not_ready`，暂停并报告 Review，得到决定后重新计算 Hash 和 Preflight。
5. 只在 Contract scope 内实现当前工单；代码/规则工单先写失败测试，文档工单先建立事实源和链接/术语检查；不得提前实现后续工单。
6. 运行 Contract 中声明的针对性检查、项目检查和场景测试；不可用工具链记录 `not_run`、原因和影响。
7. 更新 AI Change Summary，记录 changedFiles、验收映射、scenarioCoverage、guidelinesCompliance、checkpointEvidence、Intent Alignment、残余风险和未验证项。
8. 运行 `make ai-checkpoint ... STAGE=before_finish` 及全部必需 `check-ai-*`、项目质量和文档检查；失败就继续当前工单。
9. 运行 `make ai-finish TASK=<task>`，确认 Contract、Summary、Cockpit Status 和证据已归档；PR 前不得删除工单分支。
10. 推送专用分支，创建唯一对应 PR，完成审查并合并；不得用本地直接合并替代 PR。
11. PR 合并后运行 `make ai-close-work-item TASK=<task>`，确认归档、PR/分支一对一归属、远端/本地分支清理、工作树干净。
12. 同步本地默认分支并验证与远端默认分支一致；仅当命令报告 `ready for next Work Item`，才循环进入下一个工单。

## 四、串行工单列表

### 工单 1：Bootstrap Wizard 状态机与外置 Session

**目标：** 在任何 Repository 写入前完成检测、提议、用户配置、Review、Confirm、Back、Cancel、Resume 和依赖失效。

**范围线索：** Installer/Wizard、外部 Session Schema、Step Navigation、Review Summary、Back/Cancel/Resume、依赖图和状态机测试。

**验收：** Session 不落在 Repository；Cancel 不写入、不创建分支/Worktree；修改 Primary Remote 等上游输入会标记下游答案失效；中断可恢复；不唯一输入不自动选择。

### 工单 2：Repository Detection 与 Drift Revalidation

**目标：** 可靠记录 Repository Root、Commit、Branch、HEAD、Dirty Paths、Remotes、Remote HEAD、AI Cockpit 状态，并在最终写入前重新验证。

**范围线索：** Git Detection、Remote/Branch Resolver、Dirty Tree Policy、Detached HEAD、Multiple Remotes、Missing Remote HEAD、Drift Check。

**验收：** 非 Git Repository 或无 Commit 停止；状态漂移使旧确认失效；Dirty Paths 与 Write Scope 重叠时停止或切换 Worktree；最终写入使用重新验证后的基线。

### 工单 3：Bootstrap Write Boundary、Dry Run 与非交互模式

**目标：** 只写明确允许的 Runtime/治理文件，保护业务代码、CI、未知路径和未确认配置。

**范围线索：** Allowed/Forbidden Paths、Worktree Mode、Makefile Managed Block、Dry Run、Non-interactive 参数、Write Transaction。

**验收：** Dry Run 输出完整 proposed diff；最终确认前写入数为 0；Bootstrap 不修改业务代码、CI、Complexity Policy 或正式治理策略；非交互模式缺少 Required User Input 时 fail closed。

### 工单 4：Bootstrap Adoption Evidence 与 Runtime Verification

**目标：** 为首次安装生成独立 Adoption Record、Receipt、Summary 和可验证证据，并使用刚安装的 Runtime 验证结果。

**范围线索：** `adopt_ai_cockpit` Schema、Bootstrap Receipt、Evidence Bundle、Runtime Verification、Bootstrap 状态和安装文档。

**验收：** Evidence 绑定目标 Repository、基线 Commit、实际写入和验证结果；模板自身 Evidence 不冒充采用方 Evidence；Bootstrap 只显示 Runtime installed / configuration required，不宣布 Adoption Ready。

### 工单 5：Bootstrap 合并后的 Configuration Work Item 生命周期

**目标：** 把 `configure_ai_cockpit` 固化为 Bootstrap 合并后的第一个标准 Work Item，并建立 Configuration Required → Adoption Ready → Governed Development Gate。

**范围线索：** `ai-start`、Configuration Contract、状态生成器、Doctor/Calibration/Readiness 命令、Smoke 和生命周期文档。

**验收：** Configuration Work Item 使用标准 Contract/PR/归档/关闭流程；配置未完成时正式 Enforced Development 被ブロッキング；Bootstrap、Configuration 和 Governed Development 的状态在 CLI、Smoke、文档和测试中一致。

### 工单 6：Project Doctor 与 Project Profile Proposal

**目标：** 检测对象工程技术栈、模块边界、质量工具、关键领域和 Makefile 集成方式，生成可审查的 Profile Proposal。

**范围线索：** Project Doctor、Stack Detector、Profile Schema、Quality Command Registry、Critical Domain 配置和 Proposal 输出。

**验收：** 支持 Python、Flutter、TypeScript Monorepo、Java 多模块、Go 等候选；多技术栈默认使用 generic profile 并列出待确认项；提案不自动激活策略；Quality Commands 和 Critical Domains 有来源与确认记录。

### 工单 7：Adoption/Active/Work Item Complexity Baseline

**目标：** 建立 Adoption Baseline、Active Complexity Baseline 和 Work Item Base Commit，区分历史、新增和恶化复杂度。

**范围线索：** Baseline Capture、Changed Files/Modules/Lines、Dependencies、Schema/Guard/Allowlist/Archive 指标、Historical/New/Worsened 分类。

**验收：** 基线绑定 Commit；模板阈值不直接复制；历史债务默认不ブロッキング；新增和恶化复杂度可追踪；Unavailable 不等于 Allow；基线输出可复核且不用于评价个人。

### 工单 8：Complexity Policy Proposal、Human Confirmation 与 Preflight Revalidation

**目标：** 让项目复杂度政策经过提案、人工确认、激活和重新 Preflight 后才生效。

**范围线索：** Complexity Policy Schema、Policy Proposal、Approval Evidence、Policy Activation、Preflight Revalidation、Resume Conditions。

**验收：** Policy 激活前保持 Proposal 状态；每项人工决定有 Decision Evidence；预算增加必须伴随重复概念删除或有责任人的偿还计划；确认后重新计算 Preflight，旧 Hash 不可复用。

### 工单 9：Adoption Readiness 聚合门

**目标：** 聚合 Profile、Complexity Policy、Quality Commands、Critical Domains、Guards、Unknowns 和必要确认，形成可审计 Adoption Ready 判定。

**范围线索：** Readiness Evaluator、Cockpit Status、Scenario Coverage、Unknowns、Configuration Summary 和最终门禁。

**验收：** 缺 Profile、未确认 Policy、缺质量命令、未知关键领域或未解决必要 Unknowns 时不 Ready；Ready 结论引用实际证据；状态不会因 active Work Item 数为 0 而被错误推导。

### 工单 10：Lifecycle Fact Source 与多语言文档事实对齐基础

**目标：** 建立机器可读生命周期事实源，并让英文、日文、中文文档引用同一状态定义。

**范围线索：** Lifecycle Schema、Documentation Validator、README、Installation、Configuration、Upgrade、Architecture、Trust Layer 文档。

**验收：** 三阶段、状态、命令、禁止事项和边界来自同一事实源；链接、术语、元数据和中/日/英事实一致；文档不把治理证据宣传成 Sandbox、身份认证或企业合规证明。

### 工单 11：跨技术栈与长周期 Adoption 验证

**目标：** 在独立 Fixture/Adopter Repository 中验证安装、配置、正常 Work Item、模糊请求、关键领域变更、升级、回滚和发布检查。

**范围线索：** Python、TypeScript Web、Flutter 或 Java Multi-module Fixture、Adopter Harness、Upgrade/Rollback、Evidence Bundle 和 CI。

**验收：** 至少三个真实技术栈或明确记录不可用工具链；每个阶段输出原始命令和证据；覆盖 Dirty Repository、多个 Remote、Detached HEAD、Worktree、Drift、Resume、Duplicate Bootstrap；不把 Manifest Simulation 写成真实执行。

### 工单 12：进行妄想测试，不通过的话继续修改

**目标：** 对无证据声明、证据矛盾和荒诞危险场景做强制回归门；不通过就继续修改，或创建新的单一修复工单并完整闭环。

**测试内容：** 造火箭的中/英/日及委婉表达；支付“永远成功”的多语言、无敏感词和不同路径包装；删除所有测试；跳过 Checker；“随便改改/看起来差不多”且缺少 Target、Expected Outcome、Success Criteria；同时验证合法文档、sandbox mock、登录错误测试等低风险正例。

**验收：** 负例在 Enforced Profile 下沿具体治理路径ブロッキング，正例通过；输出 state、原因、Evidence、Resume Condition、Policy Reference；测试结果进入 Make/CI 和 Summary；失败不得进入后续三个工单。

### 工单 13：对齐现有文档

**目标：** 对齐 README、Trust Layer、Architecture、Configuration、Installation、Upgrade、Release、Enterprise Boundary、Fixture、Guard 以及中/日/英文文档。

**验收：** 文档准确区分 Bootstrap/Configuration/Governed Development、Baseline/Policy、deterministic known-risk coverage 与 semantic risk classification；更新命令、状态、边界、已验证场景和未验证项；完成链接、术语、元数据和多语言检查。

### 工单 14：发布新版本

**目标：** 仅在工单 1–13 全部完成并已 PR 合并、归档、关闭、清理分支和同步默认分支后，基于最新远端默认分支发布新版本。

**验收：** `SOURCE_COMMIT == DEFAULT_BRANCH_COMMIT`；Tag、Detached Checkout、Release Asset、Workflow、SBOM、Provenance、Evidence Digest 和兼容性证据精确绑定；Candidate/Published 状态唯一；失败不发布、不移动 Tag、不删除证据；Release Notes 不改变企业级 NO-GO 边界。

### 工单 15：清理执行计划文档

**目标：** 最后清理重复、过时或误导性的执行计划文档，同时保留可审计历史。

**验收：** 逐份标记执行中、已完成需保留、已被替代或可安全删除，并记录对应 Work Item/PR；不删除 Contract、Summary、Cockpit Status、评审/发布证据或仍被引用设计；链接、索引、重复内容和状态检查通过；本计划最终标记为历史保留，不再处于执行中；本工单关闭后不创建新的整改工单。

## 五、计划级完成定义

本计划只有在工单 1–15 严格按顺序完成，且每个工单均具备 Contract v2、针对性验证、AI Change Summary、归档记录、唯一 PR、合并记录、`make ai-close-work-item` 成功记录、分支清理和默认分支同步证据时，才算完成。

最终至少重新运行并记录：

```text
make check-ai-contract
make check-ai-scope
make check-ai-guards
make ai-checkpoint STAGE=before_finish
make check-ai-agent-risk
make check-ai-review-policy
make check-ai-backtrack
make check-ai-coverage-guard
make check-ai-guidelines
make check-ai-change-summary
make generate-cockpit-status
make check-ai-status
make check-ai-status-consistency
```

另须运行每个 Contract 声明的项目测试、Bootstrap/Drift/Fixture/Upgrade/Rollback 验证、妄想测试、文档检查和发布验证；所有 `not_run` 必须写明原因和影响。

## 六、执行循环

```text
最新远端默认分支
  ↓
专用 Work Item 分支
  ↓
Contract + Preflight → 实现 → 验证 → Summary → ai-finish/归档
  ↓
PR → Review → Merge
  ↓
ai-close-work-item → 清理本地/远端分支 → 同步默认分支
  ↓
ready for next Work Item
  ↺ 循环至工单 15 完成
```

计划完成不改变企业级安全与合规 NO-GO，也不产生“能够识别所有未知危险意图”的承诺；未来若要改变该结论，必须补齐可信身份、独立审批、权限控制、不可篡改审计、隔离、秘密管理和合规证据。
