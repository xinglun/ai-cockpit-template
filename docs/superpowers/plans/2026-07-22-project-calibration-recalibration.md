---
author: Ray
title: "Project Calibration and Update Recalibration Review Remediation Plan"
description: "评审后的项目校准、更新重新校准和串行 Work Item 闭环执行计划。"
keywords:
  - project-calibration
  - recalibration
  - review-remediation
  - work-item-lifecycle
---
# Project Calibration and Update Recalibration 评审整改执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 根据本次“项目校准与更新重新校准”评审，建立首次安装和 Runtime 更新后的可验证校准闭环，并按串行 Work Item 完成已授权整改、PR 合并、分支清理、工单1补执行、受影响的新版本发布和最终计划文档闭环。

**Architecture:** AI Cockpit 仍是 Repository Governance Layer。首次安装通过 `configure_ai_cockpit` 建立 Proposal 到 Active Project Configuration；更新先比较 Old Runtime、New Runtime 和 Current Active Configuration，再执行 `no_recalibration`、`migration_only`、`partial_recalibration` 或 `full_recalibration`。所有结果遵循 Detect → Propose → Explain → User Confirm/Correct → Validate → Activate，旧 Active Configuration 在新 Candidate 成功激活前保持权威。

**Tech Stack:** Python、pytest、Make、JSON/YAML Schema、Markdown、CI、GitHub PR、Work Item Contract v2。

## Global Constraints

- 评审材料接收日为 2026-07-22；计划编写时仓库基线为 `4ba14ba`，但每个工单必须从执行时最新远端默认分支创建，并在 Contract 记录 `baseRemote`、`baseBranch`、`baseCommit`。
- 一个工单对应一个 Work Item、一个专用分支和一个 PR；不合并无关工单，不以本地直接合并替代 PR。
- 每个工单必须使用 `contractVersion: 2`，明确 `scope`、`outOfScope`、`sources`、`unknowns`、`acceptance`、`scenarioCoverage` 和 `verification`。
- 校准输出只能先进入 Proposal/Candidate；Blocking Unknown、Stale、Invalid、冲突证据和未完成人工确认必须 fail closed。
- 默认用户交互语言、规范文档语言和生成报告语言为日语；命令、文件名、Schema 字段和机器状态保持英文。
- 不把检测推断写成事实，不把用户授权写成测试/PR/发布证据，不宣称能够理解所有模糊或未知危险意图。
- 不删除测试、Contract、Summary、Cockpit Status、评审/发布证据或仍被引用的计划；计划清理只能由最后一个独立工单执行并保留审计依据。

## 一、评审收查与总结

### 评审确认的目标状态

首次安装必须遵循：

```text
Bootstrap Adoption
→ configure_ai_cockpit
→ Full Project Calibration
→ First Active Project Configuration
→ Preflight Revalidation
→ Adoption Readiness
→ Governed Development
```

Runtime 更新必须遵循：

```text
Runtime Update
→ Preserve Current Active Configuration
→ Recalibration Impact Assessment
→ no_recalibration / migration_only / partial_recalibration / full_recalibration
→ Revalidation
→ Updated Active Project Configuration
```

完整校准范围统一覆盖十类：Repository Profile、Source Boundaries、Quality Commands and Evidence Producers、Guard and Coverage Policy、Critical Domains and Risk Types、Complexity Baseline and Policy、Ownership and Review Boundary、Security and Recovery Policy、CI/Release/Installed Lifecycle、Documentation Policy。

### 评审结论

| 范围 | 结论 |
| --- | --- |
| 模板工程继续开发 | GO |
| 内部导入与受控 PoC | GO |
| Repository Governance Template | GO with Conditions |
| 首次项目校准 | 必须由独立 `configure_ai_cockpit` Work Item 完成 |
| Runtime 更新 | 必须先做 Impact Assessment，不能把 Update 当作完成 |
| 企业级安全、身份、隔离、不可篡改审计与合规 | NO-GO，除非另有外部证据 |

### 本轮必须落实的评审要求

1. 自动检测只能产生 Detected Fact 和 Evidence；Recommended Default、Required Decision、Derived Result 必须分开显示。
2. 首次校准必须支持十个 Stage、Proposal、Stage Self-check、Full Self-check、Governance Simulation、两阶段人工确认、Drift Revalidation、Preflight 和 Adoption Readiness。
3. 更新重新校准必须保存 Current Active Value，按影响只重新打开新增、Stale、Invalid 或无法迁移的项目；未受影响的确认继续有效。
4. `K` 保留旧值仅在兼容时可见；`Unknown` 必须区分 blocking/warning/informational；`Not Applicable` 必须有理由并检查矛盾。
5. Candidate 激活必须原子化；激活失败时旧 Active Configuration 继续有效，不得留下半激活状态。
6. 所有配置依赖上游变更后必须标记下游为 `stale` 并重新确认，不能把旧值直接带入 Active Candidate。

## 二、已经得到的授权

用户已经明确授权本计划按串行方式执行以下事项，无需在每个工单前再次确认权限：

- 修改实现、测试、Schema、治理配置、CI、示例和文档。
- 为每个工单从最新远端默认分支建立专用分支，创建/更新 Contract v2、Summary 和证据记录。
- 运行本地和 CI 检查，创建、推送、评审并合并每个工单的 PR。
- 每个工单执行 `make ai-finish TASK=<task>`、归档、PR 合并后的 `make ai-close-work-item TASK=<task>`，并清理本地和远端分支。
- 全部整改后执行妄想/无证据声明回归；失败时继续在当前工单修复，或创建新的单一修复工单并重新走完整流程，直到通过。
- 对齐文档、发布新版本，并将“清理执行计划文档”作为最后一个工单。

上述授权不替代实际证据。Human Decision、PR 编号、合并 SHA、Release Tag、Workflow Run、Provider Asset、Digest、分支删除和主分支同步结果，必须在实际执行后记录。

## 三、每个工单的强制完整流程

以下流程必须完整执行，且只有第 12 步输出 `ready for next Work Item` 后才能循环到下一个工单。任一步失败，当前工单保持未完成，不得跳过、并行或提前清理分支。

1. 获取远端默认分支最新提交，发现并记录远端、默认分支和 `baseCommit`。
2. 从该基线创建专用分支；运行 `make ai-start TASK=<task> TITLE="..." MODE=code`，确认 Contract/Summary 成对存在。
3. 读取 `.ai/cockpit/README.md`、`.ai/README.md`、`.ai/glossary.md` 和相关 Contract，补齐 Intent、scope、outOfScope、sources、unknowns、acceptance、scenarioCoverage、verification、风险和能力字段。
4. 运行 `make ai-preflight`。若状态为 `needs_human_confirmation` 或 `not_ready`，暂停实现并报告 Preflight Review；得到决定后重新计算 Contract/Preflight Hash，不能复用旧证据。
5. 在当前 Contract scope 内先写失败测试，再做最小实现；不得把后续工单内容混入当前工单。
6. 运行针对性测试、项目测试和 Contract 声明的全部检查；不可用工具链记录 `not_run`、`unavailable` 或 `ci_only`，不得写成通过。
7. 更新 AI Change Summary，记录 changedFiles、验收映射、场景覆盖、guidelinesCompliance、Intent Alignment、残余风险和未验证项。
8. 运行 `make ai-checkpoint ... STAGE=before_finish` 及所有必需 `check-ai-*`、质量、文档或发布检查；失败就留在当前工单修复。
9. 运行 `make ai-finish TASK=<task>`，确认 Contract、Summary、Cockpit Status 和证据已归档；PR 前不得删除分支。
10. 推送专用分支，创建唯一对应 PR，完成评审并合并；不得用本地默认分支合并替代 PR。
11. PR 合并后运行 `make ai-close-work-item TASK=<task>`，确认归档证据、PR/分支一对一归属、远端和本地分支删除、工作树清洁。
12. 同步本地默认分支并验证与远端默认分支一致；只有确认 `ready for next Work Item` 后，才创建下一个工单。

循环关系：

```text
工单 N 完整闭环
→ PR 合并
→ ai-close-work-item
→ 本地/远端分支清理
→ 默认分支与远端同步
→ ready for next Work Item
→ 工单 N+1
```

## 三点五、实际执行状态与证据索引

本计划按第 3 节逐个执行；每个已启动工单均先建立 Contract v2 和 Summary，完成 `ai-finish` 归档，再完成 PR 检查、合并和 `ai-close-work-item`。`ai-close-work-item` 负责删除本地/远端 Work Item 分支并同步默认分支；没有在下一个工单开始前跳过该步骤。此前工单14在工单1之前关闭属于顺序错误，本次补执行工单1后重新评估并修正计划与发布依赖。

| 工单 | 实际状态 | PR / 发布证据 |
| --- | --- | --- |
| 1 One Release Truth | **已补执行并关闭** | PR #237；合并后已执行 `ai-close-work-item`，并完成 canonical/projection 影响复核 |
| 2–10 | **已完成并关闭** | 对应 PR #225–#231；各自 Contract/Summary 已归档，PR 已合并，分支已清理 |
| 独立预算修复 | **已完成并关闭** | PR #232；用户已授权的独立 Work Item，修复复杂度预算后完整关闭 |
| 11 Unsupported Claim Regression Gate | **已完成并关闭** | PR #233；正式回归门及负例/正例证据已合并并关闭 |
| 12 对齐现有文档 | **已完成并关闭** | PR #234；多语言文档与 Trust Layer/边界说明已合并并关闭 |
| 13 发布新版本 | **本 Work Item 执行中** | PR #235 与 previous historical release 作为历史发布证据保留；本 Work Item 准备 v0.5.38，合并后补齐 Tag/Run/资产证据 |
| 14 清理执行计划文档 | **需在新版本后最终对齐** | PR #236 已合并关闭；待 v0.5.38 发布证据完成后，由独立最终对齐工单补齐全部编号、SHA、Run、Tag 和关闭证据 |

WI13 的发布前 exact-SHA Smoke、Compatibility 和发布后严格 Smoke 均已成功；这些证据只证明 previous historical release 的历史发布，不替代工单1完成后的新版本发布证据。工单1补执行完成后，必须重新运行受影响的状态、分发、供应链和 Release Workflow 检查，再以新版本建立最终发布事实。

### 工单1补执行影响评估

| 影响范围 | 结论 | 对应动作 |
| --- | --- | --- |
| 已发布 previous historical release 标签、Release 和资产 | 不回改，继续作为历史证据 | 保留原 PR #235、Run `29915996900`、标签和资产；新版本使用新 Tag |
| `release-state.json` / `release.json` / `next-release.json` | 需要重新验证 canonical/projection 关系 | 工单1执行一致性 Gate、投影冲突回归测试和 Digest 校验 |
| 已合并工单2–12 | 不重做实现；只复核是否受 canonical 校验影响 | 重新运行相关状态、分发、供应链和 PR 质量检查 |
| 已关闭工单14计划文档 | 顺序证据不完整，需要补写 | 工单1记录本次修正；新版本发布完成后补齐最终 Release/关闭证据 |
| 下一版本 | 必须重新发布 | 工单1合并关闭后创建独立发布 Work Item，重新完成 Tag、Detached Checkout、Run、SBOM、Provenance、Digest 和 `ai-close-work-item` |

## 四、串行工单列表

### 工单 1：One Release Truth（P0）

统一 `release-state.json`、`release.json`、`next-release.json` 的事实源，明确 `development → candidate_prepared → candidate_verified → release_published` 状态机、版本、来源 Commit、上一版本和证据引用。验收必须包含唯一 canonical 文件、状态一致性检查、真实 Digest 约束和历史证据迁移说明。

### 工单 2：Candidate Source Commit 生命周期（P0）

解决 Candidate PR 合并后 `sourceCommit` 自引用失效。选择并固化“合并后自动计算”或“合并后冻结主分支”的生命周期；发布前验证 `SOURCE_COMMIT == DEFAULT_BRANCH_COMMIT`，失败时不发布、不移动 Tag、不删除证据。

### 工单 3：真实 Evidence Digest（P0）

拆分 `evidenceStatus` 与 `evidenceBundleDigest`；`candidate_prepared` 可为 `null`，`candidate_verified` 必须是合法 sha256，`release_published` 必须与 Provider Asset 匹配；拒绝任意状态说明字符串冒充 Digest。

### 工单 4：Raw Request Exemption 结构化（P0）

将自由文本豁免改为受控 Enum，并绑定 Policy Reference、Trigger Reference、适用范围和 `approvedBy`；高风险操作不得豁免；未知、无来源或不匹配的豁免必须 fail closed，并进入 Summary/Cockpit。

### 工单 5：Requested Operation 接入 Policy（P0）

使 `requestedOperation` 真正进入 Policy Evaluation，至少覆盖 `target/action/environment/effect/authorityRequired`，并连接 Critical Domain Guard、Capability Guard、Preflight、实际 Diff 和一致性检查；缺失 authority 或策略不允许的组合必须ブロッキング。

### 工单 6：Declared Operation vs Actual Change Guard（P0）

运行时代码改动不得通过声明为安全文档改动来绕过治理。合法文档、测试和 sandbox mock 保持可通过；实际领域、环境、权限和副作用不一致时输出结构化 Signal，并引用具体 Diff。

### 工单 7：Guard 新旧协议单向映射（P1）

把旧 `Ready/Partial/Inconsistent` 降级为由 Canonical State 派生的兼容层，统一 `allow/review/confirm/block/error/not_applicable` 等状态；Validator 拒绝双语义组合，所有 Gate 消费同一 Decision Model，保持原有 fail-closed 行为。

### 工单 8：Immutable Archive Evidence Root（P1）

引入不可变 `archive-manifest.json` 根节点，固定 Freeze Contract → Generate Summary → Hash Contract/Summary → Generate Manifest → Index 引用 Manifest Hash 的顺序；Summary 不含自身 Hash，Generated Status 不进入不可变链，重复运行结果稳定并兼容旧归档。

### 工单 9：真实 TypeScript Web Fixture（P1）

建立可安装、可构建、可测试、可升级的最小真实 TypeScript Web Fixture，执行 Install、Configure、Normal Work Item、Ambiguous Request、Critical Domain Change、Upgrade、Rollback、Release Check；所有真实执行和 `not_run` 证据必须可复核，不能把 Manifest Simulation 写成真实运行。

### 工单 10：真实 Java Multi-module Fixture（P1）

建立至少两个模块的真实 Java Fixture，执行安装、构建、测试、质量检查、升级和回滚，追踪八阶段生命周期；工具链不可用时明确 `not_run`，不能把 Manifest 记录冒充执行证据。

### 工单 11：Unsupported Claim Regression Gate（P1，强制门）

将正式协议名称限定为“无证据或与证据矛盾的外部声明”，覆盖自信但无证据、未执行却写通过、推断当事实、引用不存在文件、虚假批准和模拟结果冒充真实结果。负例必须在 Finish/PR/Release 阶段 fail closed，合法文档、sandbox mock 和错误测试对照必须通过；不通过就继续修复并重新走完整流程。

### 工单 12：对齐现有文档（P1）

让 README、Trust Layer、Architecture、Configuration、Installation、Upgrade、Release、Enterprise Boundary 及日/中/英文档与实现和证据一致。必须准确区分 deterministic known-risk coverage 与 semantic risk classification，不把 Agent 自律、记录或测试宣传为 Sandbox、身份认证、不可篡改审计或企业合规证明。

文档必须明确：Runtime 安装不等于校准完成；更新不等于 Ready；首次校准使用 `configure_ai_cockpit` 和十个 Stage；更新先执行 Impact Assessment；旧 Active Configuration 在 Candidate 激活成功前继续有效；默认语言为日语。

### 工单 13：发布新版本（P1，需在工单1后重新执行）

工单1补执行并合并关闭后，从最新远端默认分支重新发布；previous historical release 仅作为此前历史发布。验收必须重新绑定 Tag、Detached Checkout、`release.json`、Asset、Workflow Run、SBOM、Provenance 和 Digest，且不改变企业级安全/合规 NO-GO 结论。发布工单自身必须再次走第 3 节完整流程。

### 工单 14：清理执行计划文档（P2，最终文档闭环）

在全部整改和新版本证据归档后，逐份审查计划，标记“执行中 / 已完成需保留 / 已被替代 / 可安全删除”，记录对应 Work Item/PR，清理重复、过时或误导内容，完成链接、索引、重复内容和状态检查。

本工单必须把本计划标记为历史保留或按证据安全删除；不得删除 Contract、Summary、Cockpit Status、评审/发布证据或仍被引用的设计文档。由于本计划此前错误地在工单1之前关闭，工单1及其影响评估、后续新版本发布完成后，必须由同一最终文档闭环补记最终 PR/Release/关闭证据；不得把 previous historical release 当作工单1之后的最终版本。

## 五、计划级完成定义

本计划只有在工单1补执行完成、受影响的后续发布工单完成、工单14计划记录更新并且每个已启动工单均具备 Contract v2、针对性验证、Summary、归档记录、PR 编号与合并 SHA、`ai-close-work-item` 成功记录、远端/本地分支删除记录和主分支同步证据时，才算本轮执行完成。previous historical release 仅作为补执行前的历史发布证据；不得用它替代工单1之后的新版本证据。

最终至少重新运行并记录：

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
- `make delusion-regression` / `make unsupported-claim-regression`
- 每个工单 Contract 声明的项目测试、Fixture 测试、校准自检、更新影响分析、发布验证和文档检查。

## 六、首次校准与更新重新校准的最终验收

首次校准必须能从对应工单实现并验证的校准入口开始，并且不会自动接受 Proposal。工单1补执行及其影响评估必须先完成，以下入口要求才可作为最终计划证据。启动 Work Item 的现有入口为：

```sh
make ai-start TASK=configure_ai_cockpit TITLE="Configure AI Cockpit for this project" MODE=code
```

更新必须先执行对应工单实现并验证的 Recalibration Impact Assessment 入口，输出四种影响结果之一。只有影响结果为 `partial_recalibration` 或 `full_recalibration` 时，才启动重新校准 Work Item：

```sh
make ai-start TASK=recalibrate_ai_cockpit TITLE="Recalibrate AI Cockpit after update" MODE=code
```

最终零容忍指标：

```text
Blocking Unknowns activated: 0
Stale or invalid values activated: 0
Updates without impact assessment: 0
Unaffected confirmations unnecessarily invalidated: 0
Old Active Configuration overwritten before successful activation: 0
Activation failures that remove old configuration: 0
Update declared ready before recalibration completion: 0
Evidence claims without executable evidence: 0
Work Items entering the next item before PR/merge/close/branch cleanup: 0
```

本计划的产品边界结论保持不变：完成这些整改只证明结构化、可复现、证据支持的治理边界更完整；不会产生“理解所有自然语言危险意图”、企业级身份认证、权限控制、隔离、不可篡改审计或合规证明。
