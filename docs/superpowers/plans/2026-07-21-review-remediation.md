---
author: Ray
title: "2026-07-21 Review Remediation Execution Plan"
description: "以 41b5f66 为基准，收敛 Release、Guard、Evidence、Fixture 和文档边界的串行整改计划。"
keywords:
  - review-remediation
  - release-state
  - guard-protocol
  - evidence-root
  - work-item-lifecycle
---
# 2026-07-21 最新评审整改执行计划
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
**Goal:** 以 2026-07-21 最新 `main`、提交 `41b5f66` 为基准，把本轮评审发现的多重事实源、双重决策语义、可伪造证据占位符和不完整 Fixture 证据收敛为可审计的串行整改闭环。
**Architecture:** 继续保持 AI Cockpit 是 Repository Governance Layer，而不是 Agent Runtime、Sandbox、身份系统或企业合规产品。整改顺序先处理发布真相和证据根，再处理 Guard 决策模型、操作声明与实际 Diff 的一致性，随后补齐真实技术栈执行证据、复杂度偿还和正式命名；最后执行妄想/无证据声明回归、文档对齐、发布和计划清理。每个 Work Item 都独立完成 Contract → 实现 → 验证 → Summary → `ai-finish` → PR → 合并 → `ai-close-work-item` → 分支清理 → 主分支同步，完成后才进入下一个。
**Tech Stack:** Python、pytest、Make、JSON/YAML、Markdown、GitHub PR/Release、Work Item Contract v2。
## Global Constraints
- 评审基准固定为 2026-07-21 的 `main` 提交 `41b5f66`；执行每个工单前重新获取远端默认分支最新提交，并在 Contract 记录 `baseRemote`、`baseBranch`、`baseCommit`。
- 一个工单对应一个 Work Item、一个专用分支和一个 PR；不并行、不跨工单共享分支、不用本地直接合并替代 PR。
- 每个 Work Item 使用 `contractVersion: 2`，显式填写 `scope`、`outOfScope`、`sources`、`unknowns`、`acceptance`、`scenarioCoverage` 和 `verification`。
- 保持 Evidence over Self-Declaration：Agent 的声明、聊天授权、非 Digest 占位文本和未执行工具链结果都不能作为已完成证据。
- 缺失、过期、冲突或无法绑定的证据必须 fail closed；`candidate_verified` 和 `release_published` 不得使用伪 Digest。
- 不宣称理解所有自然语言危险意图；只对已结构化、可复现、由策略和执行证据支持的边界作结论。
- 不删除 Contract、Summary、Cockpit Status、测试、评审证据、发布证据或设计文档。计划清理只能删除明确安全且无引用的计划副本，并记录依据。
- 每个工单完成前必须记录实际 PR、合并 SHA、归档路径、`ai-close-work-item` 结果、分支删除结果和主分支同步结果。
## 一、评审总结
### 当前工程状态
本轮评审确认工程已具备：Canonical Release State Machine 的初步入口、Guard Signal Protocol 的统一字段方向、Python/TypeScript Web/Java multi-module Fixture 表达、Delusion Scenario Regression Gate、文档边界收敛，以及新版本 Candidate 准备工作。
总体结论如下：
| 范围 | 结论 |
| --- | --- |
| 模板工程继续开发 | GO |
| 内部导入与受控 PoC | GO |
| Repository Governance Template | GO with Conditions |
| Trust Layer V1 | GO with Conditions |
| Enforced Stop 生命周期 | 基本 GO |
| 发布和供应链证据链 | Conditional GO |
| 多技术栈导入证据 | Partial GO |
| 企业级安全与合规产品 | NO-GO |
| 面向外部公开 Demo | 可以开始，但必须准确限定能力 |
准确定位是：AI Cockpit 能够对结构化、可识别、有策略依据的风险实施协议级停止；不能宣称普遍理解所有模糊、危险或越权自然语言意图，也不能替代可信身份、独立审批、不可篡改审计、Branch Protection、Protected Environment、签名 Attestation、Secret Management、运行时隔离或法律/行业合规映射。
### 本轮已经确认的进展
1. Guard 信号开始具备 `signalId`、`state`、`confidence`、`evidence`、`policyReference`、`humanDecisionAllowed`、`safeAlternatives`。
2. 三种技术栈已能表达八个生命周期阶段，并诚实区分 Python 的本地执行证据与不可用工具链的 `not_run`。
3. `release-state.json` 提供 `state`、`releaseTag`、`sourceCommit`、`previousRelease`、`evidenceBundleDigest` 的单一概念入口。
4. Work Item 已开始记录 `rawUserRequest`、`rawRequestSource`、`declaredIntent` 和 `requestedOperation`。
### 本轮发现的核心问题
- `release-state.json`、`release.json`、`next-release.json` 仍表达互相冲突的版本和状态，尚未形成 One Release Truth；评审中的 Candidate 版本不能在本计划中当作已发布事实。
- 评审中的 Candidate `sourceCommit` 在 Candidate PR 和计划清理 PR 合并后已落后于当前 `main`，暴露 Candidate Source Commit 的自引用问题。
- `evidenceBundleDigest` 允许 `local-verification-pending-provider-assets` 这类非 Digest 占位符，违反证据语义。
- Guard 新字段与旧 `Ready/Partial/Inconsistent` 仍是可自由并存的双语义，可能出现 `state=block` 但旧值为 `Ready`。
- TypeScript Web 与 Java multi-module 当前主要是 Manifest Fixture，不能写成三个真实技术栈都已端到端执行。
- `rawRequestExemption` 仍可能是自由文本绕过入口；需要 Enum、Policy、Trigger、适用范围和审计证据。
- `requestedOperation` 尚未证明被 Critical Domain Guard、Capability Guard、Preflight、Policy 和实际 Diff 一致性检查真正消费。
- “Delusion”正式含义应限定为外部声明缺乏证据或与证据矛盾，建议正式架构名使用 `Unsupported Claim Regression Gate` 或 `Evidence Contradiction Gate`。
- Archive Evidence Hash 多次人工修复，说明需要不可变 `archive-manifest.json` 根节点和固定生成顺序。
- Complexity Budget 持续上调而缺少偿还机制，必须把预算增长与重复概念减少或偿还计划绑定。
## 二、已经得到的授权
用户已经明确授权本计划按串行方式执行以下事项，不需要在每个工单前再次确认权限：
- 修改实现代码、测试、Schema、治理配置、CI、示例和文档。
- 为每个工单从最新远端默认分支创建专用分支，并建立/更新 Contract v2、Summary 和证据记录。
- 运行本地和 CI 检查，创建、推送、审查和合并每个工单对应的 PR。
- 每个工单执行 `make ai-finish TASK=<task>`、归档、PR 合并后的 `make ai-close-work-item TASK=<task>`，并清理本地和远端工作分支。
- 全部整改后执行妄想/无证据声明测试；不通过就继续修改或创建单一修复工单，并重新走完整流程，直到通过。
- 对齐现有文档、发布新版本，最后清理执行计划文档。
上述授权不允许伪造证据。具体 Human Decision、PR 编号、合并结果、发布 Tag、Workflow 运行结果、Provider Asset、Digest、分支删除和主分支同步仍必须以实际记录为准。
## 三、每个工单的强制完整流程
以下流程适用于工单 1–15；任何一步失败，当前工单保持未完成，不得进入下一工单：
1. 获取远端默认分支最新提交，记录 `baseRemote`、`baseBranch`、`baseCommit`。
2. 从该基线创建专用分支；运行 `make ai-start TASK=<task> TITLE="..." MODE=code`，并确认 Contract/Summary 成对存在。
3. 读取 `.ai/cockpit/README.md`、`.ai/README.md`、`.ai/glossary.md` 和相关现有 Contract；补齐 Intent、scope、outOfScope、sources、unknowns、acceptance、scenarioCoverage、verification、风险和能力字段。
4. 运行 `make ai-preflight`。若出现 `needs_human_confirmation` 或 `not_ready`，暂停实现，向用户报告 Preflight Review；得到决定后重新计算 Contract/Preflight Hash，不能复用旧证据。
5. 在当前 Contract scope 内先写失败测试，再做最小实现；不得把后续工单内容混入当前工单。
6. 运行针对性测试、项目测试和 Contract 中声明的所有检查；不可用工具链必须记录 `not_run`，不得写成通过。
7. 更新 AI Change Summary，记录 changedFiles、验收映射、scenario coverage、guidelinesCompliance、Intent Alignment、checkpointEvidence、残余风险和未验证项。
8. 运行 `make ai-checkpoint ... STAGE=before_finish`，再运行 Contract 要求的全部 `check-ai-*`、质量、文档或发布检查；失败就留在当前工单修复。
9. 运行 `make ai-finish TASK=<task>`，确认 Contract、Summary、Cockpit Status 和证据已归档；PR 前不得删除分支。
10. 推送专用分支，创建唯一对应 PR，完成评审并合并；不得直接在本地默认分支合并。
11. PR 合并后运行 `make ai-close-work-item TASK=<task>`，确认归档证据、PR/分支一对一归属、远端和本地分支删除、工作树清洁。
12. 同步本地默认分支并验证与远端默认分支一致；只有得到 `ready for next Work Item`，才开始下一个工单。
## 四、串行工单列表
### 工单 1：One Release Truth（P0）
**目标：** 消除 `release-state.json`、`release.json`、`next-release.json` 的三重事实冲突，选择并实现真正的单一事实源或 Canonical Index 方案。
**范围线索：** `release-state.json`、`release.json`、`next-release.json`、Release Schema、Release Workflow、发布检查、相关测试和分发文档。
**验收：** 明确唯一事实源；`previousRelease` 与真实 published release 一致；candidate tag 不与 legacy candidate 冲突；published/candidate 状态唯一；引用 Digest 匹配；无跳号或重复 Candidate；新增并通过 `check-release-state-consistency`。
### 工单 2：Candidate Source Commit 生命周期（P0）
**目标：** 解决 Candidate PR 合并后 `sourceCommit` 立即过期的自引用问题。
**范围线索：** Release Candidate Workflow、Candidate Schema、默认分支绑定检查、Tag/Draft Release 逻辑和发布文档。
**验收：** 选择并固化“合并后 Commit 自动计算并写入外部 Artifact”或“Candidate 合并后冻结 Main 直至发布”的模型；发布前 `SOURCE_COMMIT == DEFAULT_BRANCH_COMMIT` 的检查语义明确；Candidate 不因自身合并而失效；失败不发布、不移动 Tag、不删除证据。
### 工单 3：真实 Evidence Digest（P0）
**目标：** 禁止把状态说明伪装成 `evidenceBundleDigest`。
**范围线索：** Release State Schema、Evidence Bundle 生成器、Release Workflow、Provider Asset 校验和测试。
**验收：** 拆分 `evidenceStatus` 与 `evidenceBundleDigest`；`candidate_prepared` 可为 `null`；`candidate_verified` 必须是合法 sha256；`release_published` 必须存在且匹配 Provider Asset；校验器拒绝任意占位字符串。
### 工单 4：Raw Request Exemption 结构化（P0）
**目标：** 防止通过自由文本 `rawRequestExemption` 绕过原始请求证据。
**范围线索：** Contract Schema、Raw Request Guard、`.ai/policies/raw-request-exemptions.yaml`、Release/Automation Contract、Preflight、Summary 和测试。
**验收：** Exemption 使用受控 Enum，绑定 Policy Reference、Trigger Reference、适用范围和 `approvedBy`；高风险操作不得豁免；Exemption 出现在 Summary 和 Cockpit；未知、无来源或自由文本豁免 fail closed。
### 工单 5：Requested Operation 接入 Policy（P0）
**目标：** 使 `requestedOperation` 成为 Policy Evaluation 的输入，而不仅是 Contract 中的声明字段。
**范围线索：** Requested Operation Schema、Critical Domain Guard、Capability Guard、Preflight、Policy Evaluation、Summary 和负例测试。
**验收：** 建立 `Requested Operation → Policy Evaluation → Actual Diff Classification → Consistency Check` 链；`target/action/environment/effect/authorityRequired` 的组合进入策略判定；不合法组合、缺失 authority 或 Policy 不允许的组合 fail closed；Summary 能证明实际 Diff 与声明一致。
### 工单 6：Declared Operation vs Actual Change Guard（P0）
**目标：** 让把危险运行时代码改动描述成安全文档改动的绕过方式 fail closed。
**范围线索：** Diff 分类器、Contract scope/operation、文件边界 Guard、Preflight/Finish/PR Gate、测试。
**验收：** Contract 声明 `effect=document` 但实际修改运行时代码时 fail closed；实际领域、环境、权限和副作用与声明不一致时给出结构化 Signal；合法文档、测试和 sandbox mock 对照仍可通过；证据引用具体 Diff。
### 工单 7：Guard 新旧协议单向映射（P1）
**目标：** 将 Legacy `Ready/Partial/Inconsistent` 变为 Canonical State 的派生兼容层，消除双语义自由组合。
**范围线索：** Guard 返回模型、Validator、Preflight/Finish/PR/Release Gate、旧消费者、Schema、测试和迁移文档。
**验收：** Canonical State 使用统一枚举（至少 `allow/review/confirm/block/error/not_applicable`）；Legacy value 只能由 Canonical State 单向生成；Validator 拒绝不合法组合；所有 Gate 消费同一 Decision Model；既有 fail-closed 行为不削弱。
### 工单 8：Immutable Archive Evidence Root（P1）
**目标：** 通过不可变 `archive-manifest.json` 消除 Contract、Summary、Archive Path、Index 和 Digest 的循环修复。
**范围线索：** Archive/Finish 脚本、Contract/Summary Hash 生成、Archive Index、Cockpit Status、Evidence Binding Gate 和测试。
**验收：** 固化顺序为 Freeze Contract → Generate Summary（排除自引用）→ Hash Contract → Hash Summary → Generate Archive Manifest → Index 只引用 Manifest Hash；Summary 不含自身 Hash，Generated Status 不参与不可变链；重复运行结果稳定，旧归档可兼容读取。
### 工单 9：真实 TypeScript Web Fixture（P1）
**目标：** 将 TypeScript Web Fixture 从 Manifest Simulation 提升为可安装、可构建、可测试、可升级的最小真实 Fixture。
**范围线索：** Fixture 目录、`package.json`、锁文件、源代码、测试、质量命令、Adoption Harness、证据文档。
**验收：** 真实执行 Install、Configure、Normal Work Item、Ambiguous Request、Critical Domain Change、Upgrade、Rollback、Release Check；记录 npm 安装、build、test、lint 和未执行步骤；生成可复核 Evidence Bundle，不虚构外部仓库证据。
### 工单 10：真实 Java Multi-module Fixture（P1）
**目标：** 将 Java multi-module Fixture 从 Manifest Simulation 提升为真实模块路径和生命周期执行证据。
**范围线索：** Java Fixture、`pom.xml` 或 Gradle 文件、模块源代码与测试、升级/回滚脚本、CI 和证据文档。
**验收：** 至少两个模块真实安装、构建、测试、质量检查和升级/回滚；生命周期八阶段结果可追踪；工具链不可用时明确 `not_run`；不把 Manifest 记录写成真实执行。
### 工单 11：Unsupported Claim Regression Gate（P1）
**目标：** 将正式架构名称从“检测 LLM 内部妄想”收敛为“检测无证据或与证据矛盾的外部声明”。
**范围线索：** Delusion Scenario Gate、Summary/Contract/Evidence Hash 校验、命名、Make/CI、测试和 Trust Layer 文档。
**验收：** 覆盖“自信但无证据”“检查未跑却写通过”“把推断当事实”“引用不存在文件”“声称得到批准”“模拟结果冒充真实结果”；正式协议使用 `Unsupported Claim Regression Gate` 或 `Evidence Contradiction Gate`，Demo 可保留 Delusion 别名；不通过时让 Finish/PR/Release fail closed。
### 工单 12：治理复杂度偿还机制（P2）
**目标：** 防止每次新增能力都只通过提高预算来掩盖复杂度增长。
**范围线索：** Complexity Policy、Budget Validator、Schema/Guard 统计、安装 Allowlist、Archive 增长统计、Make/CI 和开发文档。
**验收：** 至少增加模块行数、单函数复杂度、Schema 数量、Guard 数量、重复协议字段、循环依赖、安装 Allowlist、Archive 增长量和 Generated Evidence 占比指标；每次预算上调必须同时删除重复概念或记录有责任人的偿还计划；预算检查仍是限制工具而非记录工具。
### 工单 13：外部 Adopter Repository 长周期验证（P2）
**目标：** 在独立 Git Repository 中验证安装、升级、回滚、PR 和跨版本回归，明确模板能力与企业控制的边界。
**范围线索：** Adopter Harness、独立 Fixture Repository、安装/升级文档、CI、版本 Tag 和长期回归报告。
**验收：** 证据来自独立仓库和独立工作树；覆盖至少一个版本升级和回滚；记录默认分支、远端、基线 Commit、PR/合并和分支清理；不把受控 PoC 结果写成企业级身份、权限、审计或合规证明。
### 工单 14：进行妄想测试，不通过的话继续修改（P1，强制门）
**目标：** 对经典荒诞场景、变体和合法对照进行全量回归；任何失败都不得进入文档对齐、发布或计划清理。
**测试内容：** 造火箭（中/英/日及委婉等义表达）、支付永远成功（多语言、无敏感名词、不同路径包装）、删除所有测试、跳过 Checker、随便改改且没有可测成功标准；同时验证合法支付文档、sandbox mock、登录错误测试等对照。
**验收：** 负例在 Enforced Profile 下于正确治理路径 fail closed，正例可通过；结果包含 state、原因、evidence、resume condition、policy reference；Make/CI 和 Summary 可复核；失败时留在本工单修复或创建新的单一修复工单，并重新走本计划第三节的完整流程，直到全部通过。
### 工单 15：对齐现有文档（用户指定）
**目标：** 对齐 README、Trust Layer、Architecture、Configuration、Installation、Upgrade、Release、Enterprise Boundary、Fixture、Guard 和中/日/英文文档。
**验收：** 准确区分 deterministic known-risk coverage 与 semantic risk classification；更新 Release State、Guard State、Archive Manifest、Fixture 等实际边界；不宣称 Sandbox、可信身份、不可篡改审计或企业合规；完成链接、术语、元数据和中/日/英一致性检查。
### 工单 16：发布新版本（用户指定）
**目标：** 仅在工单 1–15 全部 PR 合并、归档、分支清理和主分支同步后，基于最新远端默认分支发布新版本。
**验收：** `SOURCE_COMMIT == DEFAULT_BRANCH_COMMIT`；版本、Tag、Detached checkout、Release Asset、Workflow Run、SBOM、Provenance、Evidence Bundle Digest 和兼容性证据精确关联；Candidate/Published 状态唯一；失败不发布；Release Notes 保持企业级 NO-GO 边界。
### 工单 17：清理执行计划文档（用户指定，最后一项）
**目标：** 在全部整改和新版本证据归档后，清理重复、过时或误导性的执行计划，同时保留审计历史。
**验收：** 逐份标记执行中、完成需保留、已被替代或可安全删除，并记录 Work Item/PR；不删除 Contract、Summary、Cockpit Status、评审/发布证据或仍被引用的设计；链接、索引和状态检查通过；本计划最终标记为历史保留，不再处于执行中；本工单关闭后不再创建新的整改工单。
## 五、计划级完成定义
本计划只有在工单 1–17 严格按顺序完成，并且每个工单都有 Contract v2、验证结果、Summary、归档记录、唯一 PR、合并记录、`ai-close-work-item` 成功记录、分支清理记录和主分支同步证据时，才算完成。
在最后一个工单结束前，至少重新运行并记录：
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
另须运行各工单声明的项目测试、`check-release-state-consistency`、Archive Manifest 检查、Fixture 测试、Unsupported Claim Regression Gate、文档链接/术语检查和最终发布验证。所有未运行命令必须写明原因和影响。
计划完成不改变企业级安全与合规 NO-GO，也不产生“能够识别所有未知危险意图”的产品承诺。若未来要改变该结论，必须另有可信身份、独立审批、权限控制、不可篡改审计、隔离、秘密管理和合规证据。
