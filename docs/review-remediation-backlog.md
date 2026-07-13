---
author: Ray
title: "Review Remediation Backlog"
description: 原始验收指摘的整改任务拆分与依赖关系。
keywords:
  - ai-cockpit
  - review
  - remediation
  - work-items
---

# 原始评审整改任务清单

基准来源：2026-07-13 原始验收指摘。此清单把评审问题拆成可独立建立 Contract、验证和归档的 Work Item。历史 Work Item 已归档不代表对应问题自动 Closed；必须以本清单的验收证据重新确认。

## 执行顺序

按依赖关系执行：`R0` → `R1` → `R2/R3/R4` → `R5/R6` → `R7/R8` → `R9` → `R10` → `R11`。

## 阻塞级任务

### R0 治理基线与历史归档恢复

- 目标：恢复或证明历史 Summary 的不可变性，建立当前全部变更的唯一 Work Item 归属。
- 范围：历史归档修改、当前工作区 ownership、`check-ai-diff-ownership`、`check-ai-pr`、no-active 分支门禁。
- 验收：历史归档不再被原地升级；全部当前变更由单一 v2 Work Item 或有效归档 Work Item 覆盖；ownership/PR 错误归零。
- 依赖：无。后续所有验收以 R0 的干净基线为前提。

### R1 Git 信任根隔离

- 目标：所有公共 Git 入口都隔离外部 `GIT_DIR`、`GIT_WORK_TREE` 等环境变量。
- 验收：在外部 Git 环境变量指向另一仓库时，`current_head`、diff、scope、状态、PR、归档证据仍绑定目标仓库；包含回归测试。
- 依赖：R0。

### R2 供应链证据模型去自引用

- 目标：移除源码内 SBOM/provenance 对当前 HEAD 的自引用提交设计。
- 验收：源码基线不再声称绑定自身提交；CI 或 release artifact 能基于明确 source commit 生成并验证证据；文档说明生成、更新和提交边界。
- 依赖：R1。

### R3 SBOM 完整性与锁定语义

- 目标：补齐 workflow Action、直接依赖和传递依赖的 SBOM 发现，明确 lock hash 与 `--require-hashes` 的真实保障范围。
- 验收：22 个 workflow `uses` 均被正确识别；全新环境安装包与 SBOM 覆盖关系有可重复报告；文档不再夸大“锁定供应链”。
- 依赖：R2。

### R4 采用方供应链边界

- 目标：安装器不把模板仓库的 SBOM、provenance、Bandit baseline 当作采用方证据复制出去。
- 验收：模板安装内容与模板自身证据边界明确；采用方生成自身证据；安装后检查不会接受模板旧证据冒充项目证据。
- 依赖：R2、R3。

### R5 Secret scan 覆盖与脱敏完整性

- 目标：扫描未跟踪文件，并覆盖无结束标记的长私钥片段等可复现漏检路径。
- 验收：未跟踪秘密和截断私钥样本均被检测/脱敏；扫描范围、误报边界和失败行为有测试。
- 依赖：R1。

### R6 公开发布和匿名安装闭环

- 目标：提供真实可匿名访问、内容与 `release.json` 一致的发布版本。
- 验收：全新匿名环境执行 Quick Install、安装、升级、回滚；仓库、RAW、REF、SHA、摘要、tag、SBOM、provenance、lock 和脚本互相一致；不能用本地或自定义源替代公开验证。
- 依赖：R2、R3、R4、R5。

## 高优先级治理任务

### R7 归档所有权与恢复判定

- 目标：消除同一提交多任务归档时按秒级时间戳和路径排序产生的任意性，并让 no-op restore 判断使用当前工作区事实。
- 验收：重叠归档 claim 有稳定、可解释的选择规则；历史 Summary 修改不能被错误豁免；有同提交多归档和工作区恢复回归测试。
- 依赖：R0。

### R8 Work Item 证据强制化与生命周期原子性

- 目标：强制 Summary 绑定 `worktreeDigest`，禁止 `ai_finish` 猜测错误归档目标，并保证 `ai-start` 并发创建的原子性。
- 验收：缺少源码绑定的 Summary、错误年份/同名归档、并发创建均 fail closed；有并发和错误目标回归测试。
- 依赖：R0、R1。

### R9 状态模型与门禁一致性

- 目标：让状态生成器与检查器使用同一 ownership reconciliation，并确保 no-active 分支仍执行完整 diff ownership/PR 门禁。
- 验收：生成的状态可被检查器接受；无 active 时仍能发现未归属变更；`make check-ai` 与最终 PR 门禁结论一致。
- 依赖：R0、R7、R8。

## 文档与采用体验任务

### R10 文档事实与可执行示例收口

- 目标：修正 README 覆盖率、public release、安装状态、SECURITY 联系方式、CODEOWNERS 占位符，以及 Quick Install、升级、Calibration、Supply-chain、Architecture、First Work Item 的不一致。
- 验收：文档中的变量、仓库、REF、RAW、SHA、release tag、降级语义与实现一致；所有关键示例进入可执行测试；模板占位符被明确标记或替换。
- 依赖：R4、R6、R9。

### R11 最终复验与 GO/NO-GO 证据包

- 目标：在干净 checkout、CI 和匿名环境重新执行全部最终门禁，形成可审计验收包。
- 验收：Python 3.11/3.14、质量检查、治理门禁、发布安装/升级/回滚、供应链证据和文档示例均有原始输出与 commit 绑定；所有剩余风险有明确 owner 和处置结论。
- 依赖：R0-R10 全部完成。

## 状态规则

- `Closed`：实现、项目测试、AI 门禁和必要外部证据全部通过。
- `Partial`：已有历史修复，但原始验收条件或外部证据仍缺失。
- `Open`：尚未形成满足验收条件的实现或证据。
- `Blocked`：需要仓库公开化、发布权限或人工决策，不能由本地代码修改单独完成。

初始状态：R0-R11 均为 `Open` 或 `Partial`，不得根据“active 工单为 0”判定为 `Closed`。
