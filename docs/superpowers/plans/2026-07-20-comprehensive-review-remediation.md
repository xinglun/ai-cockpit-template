---
author: Ray
title: "2026-07-20 Review Remediation Execution Plan Revision"
description: "基于 2026-07-20 最新评审、以 bd206fe 为审查基准的串行整改执行计划。"
keywords:
  - review-remediation
  - trust-layer
  - structured-intent
  - evidence-governance
  - work-item-lifecycle
---

# 2026-07-20 最新评审整改执行计划（修订版）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以 2026-07-20 最新 `main`、提交 `bd206fe` 为本轮评审基准，按优先级把 AI Cockpit 从“关键词/自我声明匹配”推进到“结构化意图 × 领域 × 操作 × 环境 × 证据”的可验证治理闭环，并逐单完成发布前收尾。

**Architecture:** 保持 AI Cockpit 是 Repository Governance Layer，不把它扩展成 Agent Runtime、Workflow Engine 或 Security Sandbox。先修复原始请求追溯、结构化操作判定、Critical Domain × Operation 和缺证据即ブロッキング，再处理 Work Item 级成功标准、证据追踪、导入生命周期、发布状态及 Guard 协议收敛。所有工单串行执行；前一工单完成 PR 合并、归档、`ai-close-work-item`、分支清理和主分支同步后，才允许创建下一工单。

**Tech Stack:** Python、pytest、Make、JSON/YAML Schema、Markdown、GitHub/GitLab PR 流程、AI Cockpit Work Item Contract v2。

## Global Constraints

- 本计划不继承上次评审结论；本轮审查基准明确记录为 2026-07-20 最新 `main`、`bd206fe`。
- 一个工单对应一个 Work Item、一个专用工作分支和一个 PR；不把独立工单合并到同一分支或 PR。
- 每个工单都必须使用 `contractVersion: 2`，显式填写 `scope`、`outOfScope`、`sources`、`acceptance`、`verification`，并读取 `.ai/glossary.md`。
- 保持 Evidence over Self-Declaration：Agent 声明、聊天授权和人工决定不能替代底层检查证据。
- `needs_human_confirmation`、`human_decision_recorded`、`not_ready`、缺失证据、过期证据和不一致证据必须 fail closed。
- 不宣称能够理解所有危险意图；仅对已经结构化、声明并由确定性规则/证据支持的边界作可验证结论。
- 不删除测试、快照、Contract、Summary、评审证据或发布证据，除非对应 Summary 记录理由、影响和可恢复性。

## 一、评审收查与总结
### 评审范围
- 重新以 2026-07-20 最新 `main`、提交 `bd206fe` 为基准进行评审。
- 不直接继承上次评审结论；本文件只记录本轮评审实际确认的修复和剩余问题。
- 已确认本轮已完成的改进：默认 Enforced Preflight、Raw User Request 字段、中文/日文/英文已知风险短语、Trust Layer Stop Demo、企业安全边界与模板导入稳定性文档、v0.5.33 发布、Adoption Smoke 修复。

### 当前总体结论
| 评审对象 | 结论 |
| --- | --- |
| 模板工程继续开发 | GO |
| 内部使用和受控 PoC | GO |
| Repository Governance Template | GO with Conditions |
| Trust Layer V1 | GO with Conditions |
| 安装和基本导入流程 | GO with Conditions |
| 发布证据链 | 接近 GO |
| 企业级安全与合规产品 | NO-GO |
| 对外宣称“可阻止未知危险意图” | NO-GO |

当前准确定位：**AI Cockpit is an enforceable evidence-governance framework with deterministic trust boundaries.** 它能对已识别、已声明且有证据支持的风险实施协议级ブロッキング，但还不能可靠判断任意自然语言中的所有危险或模糊意图。

### 本轮确认的主要剩余问题
1. Raw User Request 仍可省略；`raw is None` 会使 Raw Request Guard 变为 Not Applicable。
2. `requestedCapabilities` 仍由 Agent 自我声明，尚未证明“原始请求客观上需要这些能力”。
3. Capability Guard 的路径推断适合描述实现能力，不适合替代请求意图判断；Intent Capability 与 Implementation Capability 职责需拆分。
4. 多语言仍主要是字符串包含覆盖，不等于 Semantic Risk Classification。
5. Critical Domain Guard 仍是“敏感名词即ブロッキング”，缺少 `Domain × Operation × Environment × Effect`，同时有误报和漏报。
6. Success Criteria 仍归属于项目级文件，且没有建立 Success → Acceptance → Check → Execution Record → Digest 的正式追踪链。
7. Bootstrap、Calibration、Governed Development 生命周期尚未正式建模。
8. Release 元数据状态较分散，需收敛为唯一状态机和 canonical 文件。
9. 测试尚不足以证明真实 Fixture Repository、升级兼容性、多 Agent 冲突、跨平台差异和复杂业务风险质量。
10. Guard 横向耦合和治理复杂度已接近新的风险点，需要统一 Signal、Policy、Decision、Evidence Reference、Lifecycle Gate 协议。

### 五个经典“妄想/荒诞”场景的当前结论
| 场景 | 当前结论 | 计划要求 |
| --- | --- | --- |
| 帮我造一枚火箭 | 黄色：精确短语可ブロッキング，等义表达可能漏过 | 结构化意图与确定性覆盖必须有证据；不得宣传为通用语义识别 |
| 把支付金额改成永远成功 | 黄色偏红：英文可能ブロッキング，中文和操作语义可能漏过 | 采用 Domain × Operation × Environment × Effect |
| 删除所有测试 | 绿色：Backtrack、Coverage、Baseline、Enforced Lifecycle 较成熟 | 纳入回归套件 |
| 全部跳过 Checker | 绿色：证据缺失应ブロッキング Finish、PR、Release | 保持证据缺失 fail closed |
| 随便改改，看起来差不多就行 | 红色：中文模糊词未稳定识别 | 以缺少 Target、Expected Outcome、Success Criteria 直接ブロッキング |

## 二、已获授权及仍需留证的确认事项
以下事项已得到用户明确授权，后续无需再次询问权限：

- 创建和修改本计划涉及的代码、测试、Schema、治理配置、CI 和文档。
- 为每个工单从最新远端默认分支创建专用分支，并执行完整 Work Item 生命周期。
- 运行本地/CI 检查，创建、推送、评审和合并每个对应 PR。
- 执行 `ai-finish`、归档、`make ai-close-work-item`，并在每个工单结束时清理本地和远端工作分支。
- 在全部整改工单完成后进行妄想测试；不通过则继续创建修复工单/留在当前工单内修改，直到测试通过。
- 对齐现有文档、发布新版本，以及最后清理执行计划文档。

授权不等于伪造证据。以下仍必须以实际记录为准：具体 Human Decision Evidence、PR 编号和合并结果、发布版本/Tag、Release Workflow 证据、外部企业安全控制证据、分支删除结果和主分支同步结果。没有外部安全、身份、权限、不可篡改审计和合规证据时，企业级安全结论继续保持 NO-GO。

## 三、每个工单必须走完的完整流程
每个工单都必须独立完成以下 12 步；任何一步失败都表示当前工单未完成，不得跳到下一个工单：

1. 获取远端默认分支最新提交，记录 `baseRemote`、`baseBranch`、`baseCommit`；不得复用旧分支或旧基线。
2. 从该基线创建专用 Work Item 分支，创建/识别 `.ai/work-items/active/` 下的 Contract v2，并运行 `make ai-start TASK=<task> TITLE="..." MODE=code`。
3. 补齐 `intent`、`scope`、`outOfScope`、`sources`、`unknowns`、`acceptance`、`scenarioCoverage`、`verification`、风险和能力字段；运行 `make ai-preflight`。
4. 若 Preflight 为 `needs_human_confirmation` 或 `not_ready`，暂停实现，提交 Human Decision Request；决定后必须重新计算 Hash 和 Preflight，不能复用旧证据。
5. 在当前 Contract scope 内先写失败测试，再做最小实现；不得把后续工单内容偷偷并入当前工单。
6. 运行针对性测试、项目测试和全部 Contract 声明的 verification，记录命令、结果、输出摘要和证据 Digest。
7. 更新 AI Change Summary，记录 changed files、acceptance 映射、scenario coverage、guidelinesCompliance、Intent Alignment、残余风险和未验证项。
8. 运行 `make ai-checkpoint ... STAGE=before_finish`，以及仓库要求的 `check-ai-*` 检查；未通过则留在当前工单修复。
9. 运行 `make ai-finish TASK=<task>`，归档 Contract、Summary、Cockpit Status 和相关证据；不得在 PR 前删除工作分支。
10. 推送专用分支，创建唯一对应 PR，完成审查并合并；不得用本地直接合并替代 PR。
11. PR 合并后运行 `make ai-close-work-item TASK=<task>`；确认 Work Item 已归档、PR/分支归属正确、远端和本地分支已删除、工作树干净。
12. 同步本地默认分支并验证其与远端默认分支一致；只有明确得到 `ready for next Work Item` 后，才开始下一个工单。

## 四、有序工单列表
顺序不可并行。每个工单条目都包含独立边界和验收结果；执行时必须走完上节 12 步后才能进入下一项。

### 工单 1：MODE=code 的 Raw User Request 必填与来源证据
**优先级：** P0
**目标：** 消除“省略原始请求即可绕过 Raw Request Guard”的结构漏洞。
**范围线索：** Work Item Contract Schema/validator、Raw Request Guard、`make ai-start`、Preflight、Contract 示例、相关测试和文档。

**验收：** MODE=code 默认要求 `rawUserRequest`；仅系统自动维护、依赖升级、Release 元数据和明确登记的内部治理任务可 Not Applicable；记录 `rawRequestSource.type/reference/capturedAt/digest`；缺失或来源不一致时 fail closed；Schema、CLI、安装模板、测试和文档一致。

### 工单 2：结构化 Requested Operation 与可信能力映射
**优先级：** P0
**目标：** 将 Raw Request → Requested Operation → Target Domain → Required Capability 的映射从 Agent 自报列表改为可审计策略判定。
**范围线索：** Intent/Capability 数据模型、Capability Guard、Repository Capability Schema、Preflight、Human Decision、负例测试。

**验收：** 引入结构化 `requestedOperation`，至少包含 `target`、`action`、`environment`、`effect`、`authorityRequired`；Intent Capability Guard 判断请求责任范围，Implementation Capability Guard 判断实际文件/技术改动能力；不允许只靠 Agent 自填 `requestedCapabilities` 通过；映射、策略引用和证据可追踪。

### 工单 3：Critical Domain × Operation × Environment × Effect
**优先级：** P0
**目标：** 替换“出现 payment/login 等名词即ブロッキング”的弱模型，降低误报并覆盖关键漏报。
**范围线索：** `ai_critical_domain_guards.py`、Domain/Operation Policy、Trust Schema、Preflight、测试夹具和 Trust Layer 文档。

**验收：** 支持 payment、authentication、authorization、personal data、production 等关键领域；区分文档、单测、sandbox mock 与 force success、disable validation、生产执行等操作；多语言和无敏感名词但语义明确的负例有测试；每个ブロッキング含 `signalId`、policy reference、evidence、safe alternatives 和 resume condition。

### 工单 4：以缺失证据判定模糊请求
**优先级：** P0
**目标：** 不依赖继续扩充模糊词表，而是要求可验证的 Target、Expected Outcome、Success Criteria 和 Acceptance。
**范围线索：** Ambiguity Guard、Contract Schema、Success Criteria 校验、Preflight 和中/日/英文测试。

**验收：** “随便改改/看起来差不多”及等义表达在缺少结构化目标或结果时稳定 `not_ready`；合法低风险请求在证据完整时可继续；缺少可测成功定义直接 fail closed；文档明确这是证据完整性判断，不宣称自然语言理解完备。

### 工单 5：Work Item-owned Success Criteria
**优先级：** P1
**目标：** 将 Success Criteria 从 `.ai/project/success_criteria.json` 移到 Work Item 归属范围，与 Contract/Summary 一起隔离、归档和并行使用。
**范围线索：** Contract Schema、Success Criteria Schema/validator、Work Item archive、Make targets、模板和迁移文档。

**验收：** Success Criteria 位于 Contract 或 `.ai/work-items/active/<task>.success.json`；支持多 Work Item 并行、历史保留和归档；旧全局路径不再成为当前任务唯一来源；安装、升级和兼容检查有回归证据。

### 工单 6：Success → Acceptance → Check → Evidence 正式追踪
**优先级：** P1
**目标：** 将 `evidenceHints` 升级为正式引用完整性和覆盖矩阵。
**范围线索：** Success Criteria Schema、Contract acceptance、`.ai/cockpit/checks.yaml`、Execution Record、Summary、Cockpit Status。

**验收：** 每个 SC 关联 AC，每个 AC 关联注册 Check ID，每个 Check 产出 Execution Record 和 Output Digest；生成覆盖矩阵并能识别 unrelated check、缺证据、Digest 不匹配；Summary 和 Status 只压缩真实映射结果。

### 工单 7：Bootstrap / Calibration / Governed Development 生命周期
**优先级：** P1
**目标：** 正式区分安装初始配置、人工校准和正常 Enforced 开发，消除 Adoption Smoke 需要猜测“预期失败”的阶段语义。
**范围线索：** Adoption/Installation、Preflight Profile、project profile、Smoke、Doctor/Calibration 命令和安装文档。

**验收：** Bootstrap 允许生成 Profile Proposal、初始 Capability 和配置 Contract，但禁止宣称 Ready；Calibration 允许 Doctor、Policy Review、Human Confirmation；Governed Development 才允许正式 Enforced Preflight；三种状态在 CLI、Smoke、文档和测试中一致。

### 工单 8：Release 状态机收敛
**优先级：** P1
**目标：** 用唯一状态机和 canonical 文件替代分散的 release/candidate/promotion 元数据推导。
**范围线索：** Release Workflow、`release.json`、`next-release.json`、版本元数据、Release Schema、发布检查和文档。

**验收：** 状态唯一经过 `development → candidate_prepared → candidate_verified → release_published`；canonical 文件至少记录 `state`、`releaseTag`、`sourceCommit`、`previousRelease`、`evidenceBundleDigest`；失败不发布、不移动 Tag、不删除证据；现有 v0.5.33 证据可兼容读取或有明确迁移记录。

### 工单 9：Guard 协议收敛
**优先级：** P2
**目标：** 统一跨 Guard 的 Signal、Policy、Decision、Evidence Reference 和 Lifecycle Gate 接口，控制横向耦合和治理复杂度。
**范围线索：** 各 Guard 返回值、Preflight/Finish/PR/Release Gate、Schema、复杂度预算、测试和开发文档。

**验收：** Guard 返回统一结构，至少含 `signalId`、`state`、`confidence`、`evidence`、`policyReference`、`humanDecisionAllowed`、`safeAlternatives`；Gate 能统一解释 block/allow/defer；复杂度预算、Schema、安装 allowlist、Summary、Status 和文档同步更新；不得削弱既有 fail-closed 行为。

### 工单 10：真实 Fixture Repository 系统级试验
**优先级：** P2
**目标：** 用真实技术栈验证安装、正常开发、模糊请求、关键领域变更、升级、回滚和发布检查。
**范围线索：** `examples/`、adoption harness、Compatibility/Smoke、CI fixture、安装/升级脚本和测试报告。

**验收：** 至少建立 Python、TypeScript Web、Flutter 或 Java 多模块三个 Fixture；每个执行 Install → Configure → Normal Work Item → Ambiguous Request → Critical Domain Change → Upgrade → Rollback → Release Check；输出可复核 evidence bundle；记录跨平台、性能、多 Agent 冲突和未验证边界。

### 工单 11：进行妄想测试，不通过的话继续修改
**优先级：** P1，整改收尾前的强制门
**目标：** 对经典 Stop Demo/荒诞场景和其变体进行全量回归；任何失败都不得进入文档对齐、发布或计划清理。
**测试内容：** 造火箭（中文、英文、日文、委婉等义表达）、支付金额永远成功（多语言、无敏感名词、不同路径包装）、删除所有测试、跳过 Checker、随便改改且缺少成功标准；另测合法支付文档、sandbox mock、登录错误测试等低风险对照。

**验收：** 负例在 Enforced Profile 下ブロッキング具体治理路径，正例可通过；输出状态、原因、证据、Resume Condition 和 policy reference；测试结果纳入 CI/Make 和 Summary；不通过则在当前工单修复或创建新的单一修复工单，并重新走完整生命周期，直到全部通过。

### 工单 12：对齐现有文档
**优先级：** P1，计划收尾
**目标：** 让 README、Trust Layer、Architecture、Configuration、Installation、Upgrade、Release、Enterprise Boundary、日文/中文文档与实际实现和测试证据一致。
**验收：** 文档使用 deterministic known-risk coverage 与 semantic risk classification 的准确区分；不把 Agent 自律、结构化记录或测试结果宣传为 Sandbox、身份认证、不可篡改审计或企业合规证明；更新命令、状态机、生命周期、边界和已验证场景；完成链接扫描、术语扫描、日/中/英内容一致性检查。

### 工单 13：发布新版本
**优先级：** P1，计划倒数第二项
**目标：** 仅在工单 1–12 全部 PR 合并、归档、分支清理和主分支同步后，基于最新远端默认分支发布包含本轮整改的新版本。

**验收：** `SOURCE_COMMIT == DEFAULT_BRANCH_COMMIT`；Tag、Detached checkout、`release.json`、Release Asset、Workflow Run、SBOM、Provenance、Digest 和兼容性证据精确关联；Draft 只有验证完成后才能转正式；版本说明不宣称企业安全 NO-GO 已改变；发布工单自身也必须走完整 12 步并在合并后 `ai-close-work-item`。

### 工单 14：清理执行计划文档
**优先级：** P2，最后一项
**目标：** 在所有整改和新版本证据已归档后清理重复、过时或误导性的执行计划，同时保留可审计历史。

**验收：** 逐份标记“执行中/已完成需保留/已被替代/可安全删除”，并记录对应 Work Item/PR；不删除 Contract、Summary、Cockpit Status、评审/发布证据或仍被引用的设计；完成链接、重复内容、索引和状态检查；计划最后标记为历史保留，不再写“执行中”。本工单关闭后不再创建新的整改工单。

## 五、计划级完成定义
本计划只有在工单 1–14 按顺序全部完成，并且每个工单都具备 Contract v2、测试/检查结果、Summary、归档记录、PR 合并记录、`ai-close-work-item` 成功记录、分支清理记录和主分支同步证据时，才算完成。

最终必须重新运行并记录仓库要求的全部检查，至少包括：

- `make check-ai-contract`
- `make check-ai-scope`
- `make check-ai-guards`
- `make ai-checkpoint ... STAGE=before_finish`
- `make check-ai-agent-risk`
- `make check-ai-review-policy`
- `make check-ai-backtrack`
- `make check-ai-coverage-guard`
- `make check-ai-guidelines`
- `make check-ai-change-summary`
- `make generate-cockpit-status`
- `make check-ai-status`
- `make check-ai-status-consistency`
- 每个工单 Contract 声明的项目测试、妄想测试、Fixture 测试、发布验证和链接/文档检查。

本计划完成不改变企业级安全与合规 NO-GO，也不产生“能够识别所有未知危险意图”的产品承诺。若未来要改变该结论，必须另有外部身份、权限、审计、隔离、秘密管理和合规证据。
