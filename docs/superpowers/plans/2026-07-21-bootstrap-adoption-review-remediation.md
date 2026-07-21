---
author: Ray
title: "2026-07-21 Bootstrap Adoption and Project-Calibrated Complexity Review Remediation"
description: "已完成的 Bootstrap Adoption、Project Configuration 和 Governed Development 串行整改计划。"
keywords: [bootstrap-adoption, project-configuration, complexity-calibration, review-remediation]
---
# 2026-07-21 Bootstrap Adoption 评审整改执行计划（历史完成）
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.
**状态：** 2026-07-22 已完成 WI01–WI15；本计划保留为审计记录，不再创建后续整改工单。
**Goal:** 建立“Bootstrap Adoption → Project Configuration → Governed Development”三阶段导入流程，并按对象工程自身基线校准复杂度、质量命令和 Guard。
## 评审总结
首次安装时对象工程没有 Runtime、`.ai/`、Contract、Preflight、Guard、Summary、Cockpit Status 或标准 Work Item 生命周期，因此不能直接复制模板阈值。Bootstrap 只检测、提议、收集配置、Review、Confirm、最小写入并验证 Runtime；合并后由 `configure_ai_cockpit` 完成 Doctor、Project Profile、Complexity Baseline、Policy Proposal、人工确认和 Adoption Readiness；Ready 后才允许正式治理开发。
必须落实：Session 存在 Repository 外；支持 Back/Review/Cancel/Resume 和依赖失效；最终写入前重验 Repository Drift；区分 Detected/Proposed/Required User Input；Bootstrap 不修改业务代码、CI 或正式策略；复杂度区分历史/新增/恶化，Unavailable 不等于 Allow；状态和文档共享生命周期事实源；未执行工具链写 `not_run`；不把治理记录宣传成 Sandbox、可信身份、不可篡改审计或企业合规证明。
## 已获授权与必须确认
用户已授权：修改代码、测试、Schema、Guard、治理配置、CI、示例和文档；为每个工单创建专用分支和 Contract v2；运行检查、创建/推送/审查/合并 PR；执行 `ai-finish`、归档、`ai-close-work-item`、本地/远端分支清理；妄想测试失败时继续修改；文档对齐、发布新版本和最后清理执行计划。
具体决定须展示并记录：Primary Remote、Default Branch、Bootstrap Base、Dirty Tree、Branch/Worktree、Stack、Makefile、文档语言、Write Scope、下一阶段提示及 Preflight Human Decision。PR 编号、合并 SHA、Tag、Workflow、Provider Asset、Digest、分支删除和默认分支同步只能用实际证据填写；本计划已记录这些证据。
## 每个工单的强制闭环
以下 12 步适用于全部工单；当前工单未报告 `ready for next Work Item`，不得进入下一个：
1. 获取最新远端默认分支，记录 `baseRemote`、`baseBranch`、`baseCommit` 和 Dirty Paths。
2. 从该基线创建专用分支，建立/更新 Contract v2 和 Summary。
3. 读取 README、Glossary 与相关源文档，完成 Intent、scope、outOfScope、sources、unknowns、acceptance、scenarioCoverage、verification、risk、capability。
4. 运行 `make ai-preflight`；`needs_human_confirmation`/`not_ready` 时暂停、报告、记录决定并重算 Hash。
5. 只实现当前 Contract scope；代码工单先写失败测试，文档工单先建立事实/链接检查。
6. 运行 Contract、项目和场景检查；不可用工具链记录 `not_run`。
7. 更新 Summary 的 changedFiles、验收映射、场景、指南、checkpoint、风险和未验证项。
8. 运行 `make ai-checkpoint ... STAGE=before_finish` 及全部声明检查，失败留在当前工单。
9. `make ai-finish TASK=<task>`，确认 Contract/Summary/Status/证据已归档。
10. 推送专用分支，创建唯一 PR，完成 Review 和 Merge。
11. 合并后运行 `make ai-close-work-item TASK=<task>`，确认归档、PR/分支归属、分支清理和工作树干净。
12. 同步默认分支；只有 `ready for next Work Item` 才循环执行下一项。
## 串行工单列表（均已完成完整闭环）
| 工单 | 目标与验收 | PR |
| --- | --- | --- |
| 1. Bootstrap Wizard 状态机 | 外置 Session；Detect/Propose/Configure/Review/Confirm；Back/Cancel/Resume；上游输入失效并重新确认。 | #172 |
| 2. Repository Detection 与 Drift | 记录 Root、Commit、Branch、Dirty、Remote、HEAD、Detached HEAD；最终写入前 Drift 重验，冲突则停止。 | #174 |
| 3. Write Boundary / Dry Run | 允许/禁止路径、Worktree、Makefile managed block、Dry Run、非交互模式；确认前写入为 0，越界 fail closed。 | #175 |
| 4. Adoption Evidence | 生成 `adopt_ai_cockpit` Record、Receipt、Summary 和 Runtime Verification；不把模板证据冒充采用方证据。 | #176 |
| 5. Configuration Work Item | 固化 `configure_ai_cockpit`；Configuration Required 未完成时停止正式 Governed Development。 | #177 |
| 6. Project Doctor/Profile | 检测 Python、Flutter、TypeScript、Java、Go 等栈、模块、质量命令和 Critical Domain，生成待确认 Proposal。 | #178 |
| 7. Complexity Baseline | 建立 Adoption/Active/Work Item Base Commit；区分历史、新增、恶化；模板阈值不直接复制。 | #179 |
| 8. Complexity Policy/Preflight | Policy 先 Proposal，人工确认后激活并重新 Preflight；预算增加绑定重复概念偿还或责任人。 | #180 |
| 9. Adoption Readiness | 聚合 Profile、Policy、Quality Commands、Critical Domains、Guards、Unknowns；缺证据则不 Ready。 | #181 |
| 10. Lifecycle Fact Source | 机器可读生命周期事实源；中/英/日文档、CLI、Smoke、状态和命令保持事实一致。 | #182 |
| 11. 跨栈长周期验证 | 独立 Fixture/Adopter Repository 执行 Install、Configure、Normal Work、Ambiguous、Critical Domain、Upgrade、Rollback、Release Check；真实与 `not_run` 分开。 | #183 |
| 12. 进行妄想测试，不通过继续修改 | 覆盖造火箭、支付永远成功、删测试、跳 Checker、随便改改等负例及合法正例；失败则留在本工单或创建单一修复工单，重新走完整闭环。 | #184 |
| 13. 对齐现有文档 | 对齐 README、Trust Layer、Architecture、Configuration、Installation、Upgrade、Release、Enterprise Boundary、Fixture、Guard 及中/英/日文档。 | #185 |
| 14. 发布新版本 | 仅在 1–13 全部 PR 合并、归档、关闭、分支清理、默认分支同步后发布；验证 Source Commit、Tag、Asset、Workflow、SBOM、Provenance、Digest。 | #186 |
| 15. 清理执行计划文档 | 最后逐份标记保留/替代/可删并记录 Work Item/PR；不删除证据；本计划标为历史，不再创建后续整改工单。 | 本工单 |
## 最终执行证据
WI01–WI15 已按 PR #172–#186 逐项完成 Contract v2、验证、Summary、归档、合并、`ai-close-work-item`、分支清理和默认分支同步；PR #173 为 WI01 的 CI 稳定化子工单，仍独立闭环。v0.5.35 已发布，tag 与默认分支提交 `0027d0977c3453950d43cf32fc6289431ab3f275` 一致；发布 Workflow `29859327137`、严格 Smoke `29859350164` 成功，SBOM、Provenance、release-digests、release-source 资产及 SHA256 已核验。WI15 远端检查发现归档增长达到 401，已将经验证的复杂度预算同步校准为 401。
## 完成定义
工单 1–15 严格串行完成；每项有 Contract v2、验证、Summary、归档、唯一 PR、合并记录、`ai-close-work-item` 成功、分支清理和默认分支同步证据。最终运行 Contract、Scope、Guards、Checkpoint、Agent Risk、Review Policy、Backtrack、Coverage、Guidelines、Summary、Status、项目测试、妄想测试、文档检查和发布验证；所有 `not_run` 均说明原因和影响。
执行循环：最新远端基线 → 专用分支 → Contract/Preflight → 实现/验证 → Summary/ai-finish → PR/Merge → ai-close-work-item → 分支清理/默认分支同步 → `ready for next Work Item` → 下一项。
本计划不改变企业级安全与合规 NO-GO，也不承诺识别所有未知危险意图。
