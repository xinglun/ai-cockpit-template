---
author: Ray
title: "Latest Comprehensive Review Remediation Execution Plan"
description: "Serial execution plan derived from the latest main-branch comprehensive review."
keywords:
  - trust-layer
  - capability-guard
  - preflight
  - multilingual
  - work-item-lifecycle
---

# 最新全面评审整改执行计划

> **当前状态（2026-07-21）：** 工单 1–7 已完成完整闭环；v0.5.33 已正式发布并验证。工单 8（本次文档清理）正在执行，完成后本计划归档，不再作为进行中的实现计划。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将最新主分支全面评审转化为一组按优先级串行执行、逐单完整闭环的整改工单，直到 Trust Layer、导入项目治理稳定性和发布证据达到可验证状态。

**Architecture:** 先处理 Trust Layer 的协议级拦截、原始意图解释和多语言/隐蔽风险识别，再验证模板自身与导入项目的稳定性，最后发布新版本并清理执行计划文档。每个工单独占一个分支和一个 PR；只有前一个工单完成归档、PR 合并、`ai-close-work-item` 和主分支同步后，才能开始下一个工单。

**Tech Stack:** Python、pytest、Make、JSON/YAML Schema、Markdown、GitHub/GitLab PR 流程、AI Cockpit Work Item Contract v2。

## Global Constraints

- 评审基线为历史记录中的 main 提交；实际执行每个工单前均重新获取远端默认分支最新提交，不复用旧分支。
- 一个工单对应一个专用工作分支和一个 PR，不把多个独立工单合并到同一分支或 PR。
- 维持 AI Cockpit 的边界：Repository Governance Layer，不扩展为 Agent Runtime、Workflow Engine 或 Security Sandbox。
- 以 Evidence over Self-Declaration 为准；Agent 解释、聊天确认和人工决定本身都不能替代底层检查证据。
- 不把“结构化执行记录”表述为密码学签名、不可篡改证明、身份认证或运行时隔离。
- 任何 `needs_human_confirmation`、`human_decision_recorded`、`not_ready` 或其他未满足前置条件，必须 fail closed；不得通过 Agent 自律绕过。
- 每个工单都必须使用 `contractVersion: 2`，并通过仓库规定的 AI 检查、项目检查和人工评审。

## 评审收查与总结

### 已取得的基础

- 产品定位已经收敛为 Repository Governance Layer，并明确了 Intent → Contract → Implementation → Verification → Summary → Cockpit → Human Decision 的主链。
- Release Source Identity 已显著加强：要求 `source_commit` 与远端默认分支当前 Commit 相等，使用精确 SHA、Tag、`release.json` 和 Release Asset 关联证据。
- Supply Chain Evidence 已形成基本闭环：锁定依赖、Lockfile 可再现性、精确 SHA Smoke/Compatibility、SBOM、Provenance、Digest 和 Workflow 关联记录。
- Human Decision Request 已具备可持久化的 Request/Evidence、Schema Validation 和可执行的 What Happened / Why It Matters / Options / Recommendation / Question / Resume Condition 结构。
- Trust Layer 文档已正确表达边界：人工决定不证明底层检查通过，决定后必须重新执行 Preflight 和项目检查，AI Cockpit 不替代 Branch Protection、CODEOWNERS、安全工具或生产权限体系。

### 当前结论

| 评审对象 | 结论 |
| --- | --- |
| 继续开发 | GO |
| 内部 PoC / 受控试用 | GO |
| Repository Governance Template | Conditional GO |
| Trust Layer 概念验证 | Conditional GO |
| 企业级安全与合规治理 | NO-GO |
| “AI Cockpit knows when to stop”经典 Demo | 尚不能稳定证明 |

### P0 拦截与判断

1. **默认仍是 advisory，而不是协议级拦截。** 当前 `gateEnabled: false`，风险发现后依赖 Agent 遵守提示；这不能证明“即使 Agent 想继续也无法通过治理路径继续”。
2. **Capability Guard 检查的是 Scope 路径推断，不是原始用户意图。** Agent 可以把“帮我造一枚火箭”自行解释为文档、脚本或测试，随后被错误判定为 Ready。
3. **模糊表达和风险识别基本只覆盖英语。** 中文、多语言、隐蔽风险以及不同项目表达方式尚未被稳定覆盖，因此不能通过设计中的中文测试。

本计划不把上述 P0 写成“已有能力”，而是把它们拆成可测试的整改工单，并把经典 Demo 作为验收证据而非宣传结论。

## 授权与需确认事项

以下范围已得到用户授权，并可作为后续工单的计划级授权：创建/修改实现所需代码、测试、治理配置和文档；为每个工单创建专用分支；运行本地与 CI 验证；创建、推送、评审和合并对应 PR；完成 `ai-finish`、归档、`ai-close-work-item`；在最后两个工单中发布新版本和清理执行计划文档。

执行时仍必须形成可审计记录的事项：

- 具体人工决策必须写入 Human Decision Evidence，不能以本计划中的授权文字代替。
- 发布版本号、发布 Tag、远端 PR 合并策略和生产/企业环境安全工具接入属于各自工单的验收证据；若仓库或平台在执行时要求交互确认，按当前工单暂停并记录，不得用聊天文字伪造证据。
- 企业级安全与合规结论在本计划完成前仍保持 NO-GO；只有外部安全、身份、权限、不可篡改审计和合规证据齐全后，才能另行改变结论。

## 每个工单的强制完整流程

以下流程是每个工单的退出条件，不是可选建议。每个工单完成后，严格按顺序循环进入下一个工单：

1. 获取远端默认分支最新提交，记录 `baseRemote`、`baseBranch`、`baseCommit`。
2. 从该基线创建一个专用 Work Item 分支，并运行 `make ai-start TASK=<task> TITLE="..." MODE=code`。
3. 补齐 Contract v2 的 `intent`、`scope`、`outOfScope`、`sources`、`unknowns`、`acceptance`、`scenarioCoverage`、`verification`、风险和能力字段；运行 `make ai-preflight`。若状态不是 `ready`，暂停并提交 Human Decision Request。
4. 只在 Contract scope 内实现该工单；先写失败测试，再做最小实现，再运行针对性检查。
5. 更新 AI Change Summary，记录 changed files、所有验证结果、场景覆盖、边界检查、残余风险、意图对齐和用户修正固化位置。
6. 运行 `make ai-checkpoint ... STAGE=before_finish`，再运行仓库要求的全部 AI 检查和项目质量/测试检查。
7. 运行 `make ai-finish TASK=<task>` 归档 Contract/Summary/Cockpit Status；检查归档证据，不得提前删除分支。
8. 推送专用分支，创建一个 PR，完成人工评审和合并。
9. PR 合并后运行 `make ai-close-work-item TASK=<task>`；确认分支删除、工作树干净、主分支与远端默认分支一致。
10. 只有第 9 步报告 `ready for next Work Item` 后，才获取新的远端基线并循环执行下一个工单。

任何一步失败都意味着当前工单未完成，必须留在当前工单内修复、复验和重新闭环；不得跳到下一个工单。

## 有序工单列表与已执行结果

截至本次文档清理，工单 1–6 已完成 Contract v2、验证、归档、PR 合并、`ai-close-work-item` 和分支清理；工单 7 也已闭环，并由 Release Workflow 发布并验证 [v0.5.33](https://github.com/spirex-ds-dev/ai-cockpit-template/releases/tag/v0.5.33)。可核验证据：[PR #133](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/133)、修复 PR [#134](https://github.com/spirex-ds-dev/ai-cockpit-template/pull/134) 及 `.ai/work-items/archive/2026/`。

企业级安全与合规结论仍保持 NO-GO；本计划完成不改变该边界。
### 工单 1：将 Preflight 从 advisory 提升为 enforced Trust Gate

**优先级：** P0
**目标：** 让 `needs_human_confirmation`、`human_decision_recorded` 和 `not_ready` 在协议路径上禁止进入 Implementation；同时提供明确的 `advisory` / `enforced` Profile，但正式模板、企业模板和经典 Demo 默认使用 `enforced`。

**范围线索：** `.ai/guards/preflight_review_policy.yaml`、Preflight CLI、Make targets、Trust Layer 文档、相关测试和 Negative Scenario。

**验收：**

- 默认配置为 `gateEnabled: true`，拦截状态至少覆盖 `needs_human_confirmation`、`human_decision_recorded`、`not_ready`。
- 只有新计算且证据一致的 `ready` 才能进入正式 Implementation 或 Finish。
- 缺失、过期、Hash/Decision/Work Item 不匹配的 Human Decision Evidence 全部 fail closed。
- advisory Profile 的兼容行为、enforced Profile 的拦截行为和经典 Demo 结果都有自动化测试及可复核输出。
- 文档不再把 advisory 行为描述为正式 Trust Layer 证明。

**工单闭环：** 完成上方“每个工单的强制完整流程”第 1–10 步；第 10 步通过后才进入工单 2。

### 工单 2：建立 Raw User Request → Declared Intent → Repository Capability 三层判定
**优先级：** P0

**目标：** Capability Guard 不再只从 `contract.scope` 路径反推能力；在 `interpretedDeliverable` 获得明确的人类确认前，不生成或接受实现 Scope。

**范围线索：** Contract Schema、Capability/Intent Guard、Preflight 数据模型、Human Decision Request/Evidence Schema、项目 Capability 声明、测试和示例。

**验收：**

- Contract 或关联 Request 结构化保存 `originalRequest`、`interpretedDeliverable`、`interpretationStatus`、`candidateInterpretations`、`humanClarificationRequired`。
- 原始意图、声明意图和 Repository Capability 三者独立比较，并保留语义收缩/转换证据。
- “帮我造一枚火箭”等多种候选解释在未澄清时返回 `needs_human_confirmation` 或 `not_ready`，不得因落入 docs/scripts/tests 路径而 Ready。
- 人工确认后重新生成 Preflight Hash，并重新运行全部项目检查；旧决定不能复用到新解释或新 Scope。
- Schema、CLI 输出、文档和 Negative Scenario 一致。

**工单闭环：** 完成强制流程第 1–10 步；仅在工单 1 已报告 `ready for next Work Item` 后开始，完成后才进入工单 3。

### 工单 3：补齐中文、多语言与隐蔽风险场景覆盖

**优先级：** P0

**目标：** 把语言和表达方式从英语关键词依赖提升为可审计的结构化场景判定；证明中文用户测试、混合语言、委婉表达和隐藏风险不会被误判为 Ready。

**范围线索：** Intent/Capability/Constraint Guard、关键词或规则表、Scenario Coverage Policy、Negative Scenario Suite、中文/日文文档和测试夹具。

**验收：**

- 中文、英文、日文及中英混合请求均有明确的 `ready`、`needs_human_confirmation`、`not_ready` 预期和证据。
- 覆盖同义表达、委婉表达、故意模糊表达、风险隐藏在 Scope 之后的表达，以及合法低风险请求，避免只增加关键词而造成误报。
- 测试证明 Agent 不能通过换语言、换路径或把危险意图包装成文档/测试来绕过 Gate。
- Scenario Coverage 报告为 `complete`，缺失覆盖时在 required gate 上 fail closed。
- 中英文/日文 Trust Layer 文档对判定边界、误报处理和人工澄清路径保持一致。

**工单闭环：** 完成强制流程第 1–10 步；只有工单 2 完整关闭后才开始，完成后才进入工单 4。

### 工单 4：验证模板工程自身可靠性与导入项目稳定治理

**优先级：** P1

**目标：** 用可重复的 adopter matrix 证明模板复制/安装后，Contract、Preflight、Summary、Status、Make 检查和 Work Item 关闭流程仍能稳定运行，而不是只在模板仓库自身通过。

**范围线索：** 安装/升级脚本、adoption readiness、examples、跨语言样例、项目 Capability/Success Criteria、兼容性 Smoke、文档和 CI。

**验收：**

- 至少覆盖 Python、Ruby、TypeScript、Go 或仓库现有代表性示例，并覆盖 Make 项目与非 Make 适配边界。
- 每个 adopter fixture 都从安装到第一个 Work Item、Preflight、Summary、Finish、Archive、Closure 完整走通。
- 模板占位符、CODEOWNERS、SECURITY、默认分支、远端和基础 Commit 等 adopter 必填项保持 fail closed。
- 安装/升级不会把模板工作分支、历史档案或机器特定凭据带入 adopter 项目。
- 生成稳定的 compatibility/adoption evidence，供后续发布工单引用。

**工单闭环：** 完成强制流程第 1–10 步；只有工单 3 关闭且其多语言场景证据归档后才开始，完成后才进入工单 5。

### 工单 5：补齐企业级安全、合规与 Trust Layer 证据边界

**优先级：** P1

**目标：** 解决当前企业级安全与合规 NO-GO 的证据缺口，或者明确将其作为外部控制依赖，避免把结构化记录误称为安全保证。

**范围线索：** Trust Layer 边界文档、发布 Provenance/SBOM/Digest 文档、安全工具接入说明、权限/身份/审计责任矩阵、组织 Review Policy Adapter。

**验收：**

- 文档明确区分 AI Cockpit 已提供的治理证据与必须由 Branch Protection、CODEOWNERS、身份系统、秘密管理、SAST/SCA、不可篡改审计和生产权限体系提供的控制。
- 每项企业控制有 owner、输入证据、验证命令/外部报告和失效时的拦截行为；没有证据的项目保持 NO-GO。
- 发布资产继续绑定 Source Commit、Tag、Workflow Run、SBOM、Provenance 和 Digest，并明确这些记录不是密码学签名。
- 若安全/合规证据依赖外部系统，则在 Summary 中记录 `unverified` 和恢复条件，不用人工批准覆盖。
- 组织审查策略适配器不会削弱模板默认的 fail-closed 边界。

**工单闭环：** 完成强制流程第 1–10 步；只有工单 4 的 adopter evidence 已归档且主分支已同步后才开始，完成后才进入工单 6。

### 工单 6：完成 Trust Layer “knows when to stop”经典 Demo 与回归套件

**优先级：** P1

**目标：** 用可重复 Demo 和 Negative Scenario 证明：面对未澄清原始意图、中文/混合语言风险、过期人工决定和 Scope 伪装时，治理路径都停止，而不是只显示一条提示。

**范围线索：** `docs/examples/trust-layer-demo.sh`、Negative Scenario Suite、Preflight/Capability/Intent Guard、Demo 文档、CI 输出。

**验收：**

- Demo 至少展示：未澄清火箭意图、中文危险表达、Scope 伪装、过期 Decision Evidence 和正常低风险请求。
- 对每个拦截场景，输出包含状态、原因、证据来源、Resume Condition 和拦截的具体治理路径。
- Demo 在 enforced Profile 下即使调用方继续尝试，也无法进入 Implementation/Finish；正常请求仍可完成。
- 运行结果被纳入 CI 或可重复的 Make target，且 Summary/Status 仅压缩真实证据。
- 文档使用“已验证的场景”表述，不宣称对所有真实世界风险完备识别。

**工单闭环：** 完成强制流程第 1–10 步；只有工单 5 的企业边界和外部控制责任已形成证据后才开始，完成后才进入工单 7。

### 工单 7：发布新版本

**优先级：** P1，计划最后第二项

**目标：** 在工单 1–6 全部合并并完成生命周期关闭后，基于最新远端默认分支发布包含整改成果的新版本。

**范围线索：** Release Workflow、版本文件、`release.json`、Source Identity、SBOM、Provenance、Release Digests、Smoke/Compatibility、发布文档和生成状态。

**验收：**

- 发布基线是远端默认分支当前 Commit；`SOURCE_COMMIT == DEFAULT_BRANCH_COMMIT`，Detached checkout、Tag、`release.json` 和资产 Source Commit 精确一致。
- Lockfile 可再现性、Smoke、Compatibility、SBOM、Provenance、Digest 和 Workflow Run 关联全部成功并可复核。
- Draft Release 只有在验证完成后才转为正式发布；失败时不发布、不移动 Tag、不删除证据。
- 版本号、变更摘要、升级说明和 Cockpit 状态反映已完成的真实工单，不提前宣称企业级安全合规已达成。

**工单闭环：** 发布工单本身也必须完成强制流程第 1–10 步；PR 合并后运行 `make ai-close-work-item TASK=publish-new-version`，确认主分支同步后才进入工单 8。发布操作已经得到用户授权，但所有具体发布证据仍必须由 Release Workflow 产生。

### 工单 8：清理执行计划文档

**优先级：** P2，计划最后一项

**目标：** 在所有整改和发布证据归档后，清理已完成、重复或过时的执行计划文档，同时保留必要的设计、评审、归档和可追溯历史。

**范围线索：** `docs/superpowers/plans/`、`docs/superpowers/specs/`、`docs/plans/`、历史索引、README/文档链接、Work Item archive。

**验收：**

- 逐份区分：仍在执行、已完成但需保留审计、已被新计划替代、可安全删除；依据和对应 Work Item/PR 写入 Summary。
- 不删除 Contract/Summary/Cockpit Status、评审证据、发布证据或仍被链接引用的设计文档。
- 删除或合并前完成链接扫描、重复内容扫描、文档索引检查和 `make check-ai-change-summary` 需要的归档一致性检查。
- 清理后的文档明确指向本计划的最终结果和历史归档，不留下断链或“执行中”误导。

**工单闭环：** 完成强制流程第 1–10 步；合并 PR 后运行 `make ai-close-work-item TASK=clean-execution-plan-documents`，确认其报告 `ready for next Work Item`。这是本计划的最后一项，关闭后再运行一次主分支状态检查，不创建新的整改工单。

## 计划级验证与完成定义

本计划文档工单完成前，执行并记录：

- `make check-ai-contract CONTRACT=.ai/work-items/active/latest-comprehensive-review-remediation-plan.contract.json`
- `make check-ai-scope CONTRACT=.ai/work-items/active/latest-comprehensive-review-remediation-plan.contract.json`
- `make check-ai-guards`
- `make ai-checkpoint CONTRACT=.ai/work-items/active/latest-comprehensive-review-remediation-plan.contract.json SUMMARY=.ai/work-items/active/latest-comprehensive-review-remediation-plan.summary.json STAGE=before_finish`
- `make check-ai-change-summary SUMMARY=.ai/work-items/active/latest-comprehensive-review-remediation-plan.summary.json CONTRACT=.ai/work-items/active/latest-comprehensive-review-remediation-plan.contract.json`
- `make generate-cockpit-status CONTRACT=.ai/work-items/active/latest-comprehensive-review-remediation-plan.contract.json SUMMARY=.ai/work-items/active/latest-comprehensive-review-remediation-plan.summary.json`
- `make check-ai-status CONTRACT=.ai/work-items/active/latest-comprehensive-review-remediation-plan.contract.json SUMMARY=.ai/work-items/active/latest-comprehensive-review-remediation-plan.summary.json`、`make check-ai-status-consistency`
- `make ai-finish TASK=latest-comprehensive-review-remediation-plan`

本计划的“完成”表示工单 1–8 已按强制流程逐一闭环、证据已归档、PR 与分支已清理。工单 1–7 的完成证据已归档；工单 8 完成后，计划本身进入历史保留状态。该状态不表示企业级安全与合规 NO-GO 已改变。
