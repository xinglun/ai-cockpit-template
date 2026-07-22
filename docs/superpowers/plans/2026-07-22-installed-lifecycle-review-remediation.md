---
author: Ray
title: "AI Cockpit Installed Lifecycle Management Review Remediation Plan"
description: "将 Installed Lifecycle Management 评审结论拆分为严格串行、可审计、带 PR 和分支清理闭环的 Work Item 执行计划。"
keywords:
  - ai-cockpit
  - installed-lifecycle
  - update
  - rollback
  - uninstall
  - review-remediation
  - work-item-lifecycle
---
# AI Cockpit Installed Lifecycle Management 评审整改执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **最终状态（2026-07-22）：HISTORICAL / 已完成。** 工单 1–15 已逐项完成 Contract v2、验证、归档、唯一 PR、合并、`ai-close-work-item`、分支清理和 main 同步；上一版已由发布 Workflow 以精确 main commit 发布。工单 16 是本计划最后一个清理工单；关闭后不得再从本计划创建新整改工单。

**Goal:** 将 AI Cockpit 从“只能安装”补齐为可记录事实、可更新、可迁移、可回滚、可停用、可保留证据卸载的完整 Installed Lifecycle，并以严格串行 Work Item 闭环交付。

**Architecture:** Bootstrap 在首次安装时生成 Install Manifest、Version、Managed Regions 和 Rollback Baseline，明确 template/project/shared/generated/historical Ownership。后续 Update、Rollback、Disable/Enable 和 Uninstall 均读取这些安装事实，不按路径猜测、不静默覆盖或删除项目拥有内容；更新使用 Old Template → New Template → Current Project 的 three-way comparison，卸载默认保留证据并使用 detached uninstaller 完成 Runtime 移除。所有能力通过 Contract v2、Summary、Cockpit Status、CLI、文档和跨版本测试形成可审计闭环。

**Tech Stack:** Python、pytest、Make、JSON/YAML、Markdown、GitHub PR/Release、Work Item Contract v2。

## Global Constraints

- 每个工单都是一个独立 Work Item、一个专用分支、一个唯一 PR；工单不得并行，也不得跨工单共享分支。
- 每个工单开始前从最新远端默认分支创建分支，并在 Contract 中记录 `baseRemote`、`baseBranch`、`baseCommit`。
- 每个工单必须使用 `contractVersion: 2`，显式填写 `scope`、`outOfScope`、`sources`、`unknowns`、`acceptance`、`scenarioCoverage` 和 `verification`。
- Update、Migration、Rollback、Disable/Enable、Uninstall 的人工确认点必须停在 `needs_human_confirmation`，不能由聊天授权替代运行时决策证据。
- Project-owned 内容默认保留；Historical 内容不可覆盖；Shared 文件只能修改声明的 Managed Region；缺失、漂移、冲突或证据过期必须 fail closed。
- 不把“未运行”写成通过；不能把模板仓库证据、Manifest 记录或状态说明冒充对象工程真实执行证据。
- 不宣称 AI Cockpit 是 Sandbox、可信身份系统、独立审批系统、不可篡改审计系统或企业级安全合规产品。
- 用户已授权本计划规定的仓库修改、专用分支、检查、PR、审查、合并、`ai-finish`、`ai-close-work-item`、分支清理、发布和最后的计划文档清理；该授权不是未来 PR、Merge、Release、Digest 或删除结果的事实证明。
- 不删除 Contract、Summary、Cockpit Status、测试、评审证据、发布证据、Historical Evidence 或仍被引用的设计文档。

---

## 一、评审总结

### 评审结论

评审材料确认，AI Cockpit 的安装生命周期缺少可追溯的安装事实和安全离场机制。仅有 Bootstrap/Install 会导致对象工程停留在旧版本、项目配置被覆盖、升级前状态无法恢复、Runtime 所属范围无法判断、证据随卸载丢失，以及安装行为形成事实锁定。

本计划的产品边界是：AI Cockpit 为对象工程提供 Repository Governance Layer 的生命周期协议和证据记录；它不替代身份、权限、独立审批、分支保护、Protected Environment、签名 Attestation、Secret Management、运行时隔离或法律/行业合规映射。

### 必须实现的生命周期事实

首次安装必须生成并持续维护：

- `.ai/install/manifest.json`：安装版本、来源、文件、Digest、Ownership 和 Managed Region 事实。
- `.ai/install/version.json`：安装版本、来源 Commit、Manifest Hash 和 Runtime State。
- `.ai/install/managed-regions.json`：Shared 文件的 Managed Region 边界和安装时 Digest。
- `.ai/install/rollback-baseline.json`：升级前可恢复的 Runtime、Managed Region、Schema 和项目配置 Hash 基线。

Ownership 至少包含 `template`、`project`、`shared`、`generated`、`historical` 五类。Update 只能更新 template 和声明的 shared region；project 默认保留；generated 可重生成；historical 默认不可变。

### 关键评审风险

- 仅按 `.ai/**` 或路径判断 Ownership，会误删 Project Policy、Work Item Archive 和 Human Decision。
- Update 若只做两方 diff，会静默覆盖用户修改过的 Runtime 或 Shared Region。
- Schema Migration 若直接编辑 Project-owned 配置，会改变阈值、Critical Domain、Approval Policy 或高风险 Gate 而没有人工确认。
- Rollback 若没有 Snapshot，会错误覆盖升级后产生的业务代码或项目配置。
- Uninstall 若依赖待删除 Runtime，自删除过程无法可靠完成；若直接清理，又可能丢失历史证据。
- Disable 若删除 CI Gate 或 Evidence，会把临时停用误变成不可审计卸载。

## 二、已经得到的授权与仍需实际确认的事项

### 已得到的授权

用户已经明确授权以下事项，并要求计划按串行方式执行，无需在每个工单前再次确认权限：

- 修改实现代码、测试、Schema、治理配置、CI、示例和文档。
- 为每个工单从最新远端默认分支创建专用分支，建立/更新 Contract v2、Summary 和证据记录。
- 运行本地和 CI 检查，创建、推送、审查和合并每个工单对应的 PR。
- 每个工单执行 `make ai-finish TASK=<task>`，PR 合并后执行 `make ai-close-work-item TASK=<task>`，并清理本地和远端工作分支。
- 失败时留在当前工单修复；需要拆分时只能创建一个有明确边界的后续修复工单，并重新走完整闭环。
- 全部生命周期能力完成后对齐文档、运行跨版本回归、发布新版本，最后执行“清理执行计划文档”。

### 必须以真实证据记录、不能由本授权代填

每个实际工单仍必须获得真实的：Primary Remote、Default Branch、Base Commit、Dirty Tree、分支名、Preflight Decision、PR 编号、Review 结果、Merge SHA、`ai-finish` 归档路径、`ai-close-work-item` 结果、分支删除结果、默认分支同步结果、Release Tag、Workflow Run、Provider Asset 和 Digest。缺少其中任一 required evidence，当前工单不得报告完成，也不得进入下一工单。

## 三、每个工单的强制完整流程

以下流程适用于工单 1–15。任何一步失败，当前工单保持未完成；只有完成第 12 步并明确记录 `ready for next Work Item`，才可循环执行下一个工单。

1. 获取远端默认分支最新提交，记录 `baseRemote`、`baseBranch`、`baseCommit`、Dirty Paths 和当前工作树状态。
2. 从该基线创建专用分支；运行 `make ai-start TASK=<task> TITLE="..." MODE=code`，确认 Contract/Summary 成对存在且 scope 覆盖本工单文件。
3. 读取 `.ai/cockpit/README.md`、`.ai/README.md`、`.ai/glossary.md` 和相关现有 Contract，补齐 Intent、scope、outOfScope、sources、unknowns、acceptance、scenarioCoverage、verification、风险和能力字段。
4. 运行 `make ai-preflight`。若为 `needs_human_confirmation` 或 `not_ready`，暂停实现，报告 Preflight Review；得到结构化决定后更新 Contract、重新计算 Hash，再继续。
5. 仅在当前 Contract scope 内实现：代码工单先写失败测试再做最小实现；文档工单先建立事实、链接和术语检查；不得混入后续工单内容。
6. 运行针对性测试、项目测试和 Contract 声明的全部检查；工具链不可用时明确记录 `not_run`、原因和影响。
7. 更新 AI Change Summary，记录 changedFiles、验收映射、scenario coverage、guidelinesCompliance、Intent Alignment、checkpointEvidence、残余风险和未验证项。
8. 运行 `make ai-checkpoint ... STAGE=before_finish`，再运行全部 `check-ai-*`、质量、文档、Fixture 或发布检查；失败就留在当前工单修复。
9. 运行 `make ai-finish TASK=<task>`，确认 Contract、Summary、Cockpit Status 和证据已归档；PR 前不得删除工单分支。
10. 推送专用分支，创建唯一对应 PR，完成评审并合并；不得直接在本地默认分支合并替代 PR。
11. PR 合并后运行 `make ai-close-work-item TASK=<task>`，验证归档证据、PR/分支一对一归属、远端和本地分支删除以及工作树清洁。
12. 同步本地默认分支并验证与远端默认分支一致；记录 `ready for next Work Item`，再进入下一项。

## 四、串行工单列表

### 工单 1：Install Manifest 与 Lifecycle Fact Source（P0）

**目标：** 建立安装事实源，为所有后续 Update、Rollback 和 Uninstall 提供可验证输入。

**范围：** Bootstrap/Install Runtime、`.ai/install/manifest.json`、`version.json`、`managed-regions.json`、`rollback-baseline.json`、Manifest Schema、Digest 计算、安装文档和测试。

**验收：** 新安装生成四类文件；Manifest 包含 installationId、版本、来源 Commit、安装时间、Installer Digest、文件 Ownership、Installed Digest 和 Source Path；Manifest Hash 写入 Version；历史证据不被覆盖；重复读取稳定；缺失或损坏 Manifest fail closed。

**验证：** Install E2E、Manifest Schema、Digest 稳定性、重复安装和损坏文件负例。

### 工单 2：Ownership Model 与 Managed Region（P0）

**目标：** 让文件和区域的所有权成为更新/卸载决策依据，禁止按路径猜测。

**范围：** Ownership Schema、文件分类器、Managed Region 解析器、Makefile/README/CI 标记、Project-owned 配置、Historical Evidence 和测试。

**验收：** `template/project/shared/generated/historical` 分类明确；Shared 只接受 BEGIN/END Managed Region；Project-owned 默认保留；Historical 不可覆盖；未知 Ownership 或缺少边界时不执行 Update/Uninstall。

**验证：** 五类 Ownership 正例、路径误判负例、Shared Region 漂移负例、Historical 修改负例。

### 工单 3：Installed Version、Status 与 Update Check（P0）

**目标：** 提供只读版本和生命周期状态查询，不在检查阶段修改 Repository。

**范围：** 计划中的 CLI `ai-cockpit-version`、`ai-cockpit-update-check`、状态模型、Version/Manifest 校验、Release Evidence 和 CLI 文档。

**验收：** 支持 `active`、`update_available`、`update_pending_confirmation`、`updating`、`rollback_available`、`disabled`、`uninstall_pending`、`uninstalled_runtime_preserved_evidence`、`purged`、`error`；输出当前版本、目标版本、Runtime State、配置状态、冲突、回滚可用性；目标 Release Tag、Source Commit、Release Evidence 和 Asset Digest 校验失败时只读失败。

**验证：** 当前版本、无更新、可更新、Manifest 缺失、Release Evidence 失配和不修改工作树测试。

### 工单 4：Three-way Comparison 与 Update Proposal（P0）

**目标：** 用 Old Template、New Template、Current Project 三方事实生成可审阅的升级提案。

**范围：** Diff 分类器、`.ai/upgrade/proposals/<upgrade-id>.json`、冲突模型、Shared Region Diff、Project-owned 影响、Migration 和 Rollback 关联。

**验收：** 分类覆盖 `unchanged_template_file`、`safe_template_update`、`project_modified_template_file`、`project_owned_file`、`shared_managed_region`、`new_template_file`、`removed_template_file`、`generated_file`、`historical_file`、`conflict`；Proposal 至少记录版本、Manifest Hash、Release Evidence、安全更新、新增/删除、冲突、Shared 变化、Migration、Baseline 影响、文档影响、Rollback Snapshot 和 Resume Condition；生成 Proposal 不写入 Runtime。

**验证：** Current Digest 等于 Installed Digest 的安全更新、项目修改冲突、Shared 修改、历史文件和新增/删除模板文件测试。

### 工单 5：Update Human Confirmation 与 Update Apply（P0）

**目标：** 在冲突和删除风险前停止，确认后按事务顺序应用安全更新。

**范围：** 计划中的 CLI `ai-cockpit-update-propose`、`ai-cockpit-update-apply`、`ai-cockpit-update`、Drift Check、Snapshot、Apply 顺序、Update Summary。

**验收：** Proposal 默认进入 `needs_human_confirmation`；选项包含应用安全更新、排除文件、取消、改变目标版本、审阅 Migration、返回；Apply 顺序固定为 Drift → Snapshot → Safe Files → New Files → Removed Files → Shared Regions → Project-owned 保留 → Migration → Generated 重生成 → Manifest 更新 → Integrity → Adoption Readiness → Smoke Test → Summary；任一步漂移或冲突未解决都不覆盖。

**验证：** 确认前零写入、确认后安全文件更新、取消、Repository Drift、冲突未解决、Apply 中断恢复和 Summary 绑定测试。

### 工单 6：Schema Migration（P0）

**目标：** 让 Project-owned 配置迁移可提案、可确认、可回溯，禁止静默修改。

**范围：** Migration Proposal/Apply、Schema Registry、复杂度/临界域/Approval Policy 配置、Migration Diff、重新确认和测试。

**验收：** Migration 明确旧字段、新字段、默认值、不可自动迁移内容、Policy 强度变化和重新确认项；Blocking 阈值、Critical Domain、Approval Policy、新高风险 Gate、Baseline 引用变化必须重新人工确认；不支持逆向迁移时明确 `partial_rollback` 或阻塞。

**验证：** 可自动迁移、需要确认、无法迁移、默认值、策略增强/减弱和错误 Schema 负例。

### 工单 7：Rollback Snapshot 与 Rollback Execution（P0）

**目标：** 使升级后的 Runtime 和 Managed Region 可恢复，同时不破坏项目业务代码和项目配置。

**范围：** `.ai/upgrade/snapshots/<upgrade-id>/`、Snapshot 内容、计划中的 CLI `ai-cockpit-rollback`、Rollback Proposal、恢复和部分回滚协议。

**验收：** Snapshot 包含 `manifest.before.json`、`version.before.json`、`managed-regions.before.json`、Runtime 文件恢复来源、Project Config Hash、Migration Plan 和 Rollback Instructions；Rollback 先验证当前安装，再提案、确认、恢复、逆向可行 Migration、重验证和 Smoke Test；不删除升级后业务代码，不覆盖升级后人工修改的 Project-owned 配置；无法完全恢复时输出 `partial_rollback` 和剩余人工操作。

**验证：** 完整回滚、当前状态失配、Project-owned 漂移、不可逆 Migration、Snapshot 缺失和部分回滚测试。

### 工单 8：Disable / Enable（P1）

**目标：** 支持临时停用而不删除 Runtime、Policy 或证据。

**范围：** 计划中的 CLI `ai-cockpit-disable`、`ai-cockpit-enable`、Runtime State、Disable Evidence、Blocking Entry、CI Managed Region 和状态文档。

**验收：** Disable 记录 Evidence、设置 `disabled`、停用 Blocking Entry、保留 Runtime/Policy/Evidence/Archive/Update/Uninstall 能力；不得静默删除 CI Gate；Enable 前重新执行 Runtime Integrity、Manifest、Project Profile、Policy 和 Adoption Readiness，全部通过才恢复 `active`。

**验证：** 停用/启用、启用前失败、Evidence 保留、CI Region 保持和重复操作测试。

### 工单 9：Preserve-evidence Uninstall Proposal（P1）

**目标：** 将卸载分成受治理准备阶段和独立执行阶段，并默认保留证据。

**范围：** `make ai-start TASK=uninstall_ai_cockpit`、Uninstall Proposal、模式选择、Drift 检查、Evidence Export、Uninstall Receipt 和文档。

**验收：** 支持 Disable、Preserve-evidence Uninstall、Purge 三种模式；Phase A 加载 Manifest、检测修改、选择模式、生成 Proposal、人工确认、导出证据、生成 Detached Uninstaller、归档 Summary；Preserve-evidence 默认删除 Runtime，保留 Bootstrap Evidence、Archive、Human Decisions、Project Policy、Complexity Baseline、Audit Evidence 和 Receipt。

**验证：** 三种模式、Modified Template、Project-owned 保留、Managed Region、取消、Drift 和 Receipt 完整性测试。

### 工单 10：Detached Uninstaller 与 Runtime Removal（P1）

**目标：** 让卸载执行器不依赖即将被删除的 Runtime，并在完成后自证移除结果。

**范围：** 外部临时目录 `<system-temp>/ai-cockpit-uninstall/<session-id>/uninstall.py`、Runtime 删除、Managed Region 删除、可选 CI 清理、Final Receipt 和移除验证。

**验收：** Detached Uninstaller 不导入对象工程 Runtime；执行 Repository Drift Check → 删除已确认 Runtime → 删除 Managed Region → 保留/导出 Evidence → 可选 AI Cockpit-only CI → Final Receipt → Runtime Removal Verification；未确认、已修改或 Ownership 不明的文件不删除。

**验证：** Runtime 完整移除、Detached 独立运行、业务文件保留、Evidence 保留、Managed Region 删除和中断恢复测试。

### 工单 11：Purge 与 Evidence Export（P1）

**目标：** 为破坏性清理建立明确阻塞、双重确认和可验证 Evidence Export。

**范围：** Purge Proposal、Purge Gate、Evidence Export Bundle、Receipt、恢复说明、Archive 和文档。

**验收：** Purge 默认禁止；必须明确选择、展示删除清单和不可恢复影响、完成人工确认并生成 Export Bundle；Purge 不能删除外部已导出的证据引用、Work Item Contract/Summary 的审计记录或项目拥有文件，除非用户在独立的破坏性流程中明确授权且 Proposal 逐项列出。

**验证：** 未确认阻塞、部分导出失败阻塞、Purge 成功、Purge 后状态 `purged`、证据校验和不可恢复提示测试。

### 工单 12：Cockpit Status、CLI、Summary 与文档对齐（P1）

**目标：** 让状态、命令、Summary 和用户文档共享同一 Lifecycle Fact Source。

**范围：** Cockpit Status、CLI 帮助、Update/Rollback/Disable/Enable/Uninstall 文档、Summary Schema、中文/英文/日文档和链接检查。

**验收：** Cockpit 显示当前/目标版本、Runtime State、配置、冲突、回滚、停用、卸载准备；Summary 记录 Upgrade ID、Manifest Hash、变更计数、冲突、Migration、Snapshot、用户决定、验证结果和残余风险；命令、状态和文档不互相矛盾；未执行工具链记录 `not_run`。

**验证：** CLI 文档示例、状态生成/检查一致性、三语术语/链接和 Summary Schema 测试。

### 工单 13：跨版本与跨栈 E2E（P1）

**目标：** 用真实可执行 Fixture 证明 Install → Configure → Governed Development → Update → Rollback → Disable/Enable → Uninstall 生命周期，不把 Manifest Simulation 当执行证据。

**范围：** Python Fixture、TypeScript Web Fixture、Java Multi-module Fixture、Adopter Harness、安装/升级/回滚脚本、CI 和 Evidence Bundle。

**验收：** 至少一个真实 Python Fixture 完整执行；TypeScript Web Fixture 可安装、构建、测试、升级、回滚；Java 至少两个模块真实安装、构建、测试和升级/回滚；工具链不可用必须 `not_run`；Evidence Bundle 区分本地真实执行、外部未执行和模拟结果；跨版本 Manifest、Schema、Rollback 和 Uninstall 结果可追踪。

**验证：** `pytest`、npm install/build/test/lint、Maven 或 Gradle 命令、Fixture 生命周期、真实/未运行证据分类和跨版本回归。

### 工单 14：生命周期安全负例与边界回归（P1，强制门）

**目标：** 证明生命周期操作不会静默覆盖、删除或伪造项目事实；任何失败都不得进入发布或计划清理。

**测试内容：** 修改过的 Template Runtime、修改过的 Shared Region、Project-owned Schema、Historical Evidence、漂移 Repository、未确认 Update/Rollback/Purge、不可逆 Migration、Detached Uninstaller 失效、把模拟结果冒充真实执行、把状态说明冒充 Digest、无证据声称已完成 PR/合并/删除分支；同时验证合法未修改 Runtime、合法文档更新、合法 Sandbox Mock 和取消流程。

**验收：** 所有负例 fail closed，正例通过；Signal 包含 state、原因、evidence、resume condition 和 policy reference；Make/CI、Summary 和 Cockpit 可复核；失败时留在本工单修复或创建单一修复工单，并重新执行第三节完整流程。

### 工单 15：发布新版本（P1，必须倒数第二）

**目标：** 仅在工单 1–14 全部完成完整闭环后，发布包含 Installed Lifecycle 的新版本。

**范围：** Release State、Tag、Detached Checkout、Release Asset、Workflow、SBOM、Provenance、Evidence Bundle、Release Notes 和兼容性文档。

**前置条件：** 工单 1–14 各自有 Contract v2、Summary、验证结果、归档记录、唯一 PR、合并记录、`ai-close-work-item` 成功、分支清理和默认分支同步证据；未满足任何一项不得发布。

**验收：** `SOURCE_COMMIT == DEFAULT_BRANCH_COMMIT`；Candidate/Published 状态唯一；Release Asset、SBOM、Provenance、Manifest、Evidence Bundle Digest 与发布 Commit 精确关联；失败不发布、不移动 Tag、不删除证据；Release Notes 明确产品边界。

**验证：** 发布前全量 AI 检查、项目测试、Fixture 回归、Release State Consistency、Digest/Asset 校验、Workflow Run 和 Detached 安装验证。

### 工单 16：清理执行计划文档（最后一项）

**目标：** 在全部生命周期整改、新版本发布和证据归档后，清理重复、过时或误导性的执行计划文档，同时保留审计历史。

**范围：** `docs/superpowers/plans/**`、`docs/superpowers/plans/README.md`、计划索引、链接/术语检查，以及本计划的最终状态标记。

**执行要求：** 逐份检查计划，标记为当前执行、完成需审计、已被替代或可安全删除；优先保留原文并补充替代关系、Work Item、PR、发布和归档证据；删除前必须完成链接扫描并在本工单 Summary 记录文件、理由和恢复路径。不得删除 Contract、Summary、Cockpit Status、评审/发布证据、设计规格或仍被引用的计划。

**验收：** 计划索引与实际状态一致；链接、元数据、术语和多语言文档检查通过；本计划标记为历史保留，不再处于执行中；本工单关闭后不再从本计划创建新的整改工单。

**验证：** 文档链接检查、计划索引一致性、引用扫描、AI Scope/Change Summary/Status 检查、`ai-close-work-item` 和本地/远端分支清理。

## 五、计划级完成定义

本计划只有在工单 1–16 严格按顺序完成，且每个工单都具备 Contract v2、Preflight、实现或文档变更、验证结果、Summary、归档记录、唯一 PR、审查结果、合并记录、`ai-close-work-item` 成功记录、分支清理记录和默认分支同步证据时，才算完成。

## 六、最终审计索引（本计划关闭后保留）

本计划的 Work Item 与 PR 对应关系为：工单 1–13 对应 PR #198–#210；工单 14 对应 PR #211；工单 15 对应 PR #212；工单 16 对应本次计划清理 PR。每个 Work Item 的 Contract、Summary、archive-manifest、归档索引和 `ai-close-work-item` 结果是审计事实源，不因本计划标记为历史而删除。

发布证据由历史发布 Workflow 生成并发布到 Release Assets：`sbom.json`、`provenance.json`、`release-digests.json`、`release-source.json`。失败路径保持不发布、不移动 Tag、不删除证据；该约束仍适用于后续独立发布计划。

工单 16 关闭前至少重新运行并记录：

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

另须运行各工单声明的项目测试、Manifest/Ownership Schema 检查、Update Proposal/Three-way Comparison、Migration、Rollback、Disable/Enable、Detached Uninstaller、Purge、Fixture、文档链接/术语、Release State、Asset Digest、SBOM、Provenance 和最终发布验证。所有未运行命令必须写明原因、影响和后续责任人。

计划完成不改变企业级安全与合规 NO-GO，也不产生“能够识别所有未知危险意图”的产品承诺。未来若要扩大该结论，必须另立 Work Item 并补充可信身份、独立审批、权限控制、不可篡改审计、隔离、秘密管理和合规证据。
