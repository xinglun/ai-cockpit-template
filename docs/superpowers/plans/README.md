---
author: Ray
title: "Execution Plan Index"
description: "Index and retention policy for auditable execution plans."
keywords:
  - execution-plan
  - audit
  - work-item
---
# Execution Plan Index

本目录保存当前执行计划和历史关闭索引。不可变 Work Item archive 是完成事实的权威来源。

## 保留规则

| 分类 | 处理方式 |
| --- | --- |
| 当前执行 | 保留原文，标注执行中并链接 Work Item。 |
| 已完成/需审计 | 引用扫描后可压缩为关闭索引；必须保留 archive evidence 路径和 Git 恢复方式。 |
| 已替代/错误计划 | 新 Work Item 完成引用扫描并记录替代证据后删除；不得删除 Contract、Summary 或 manifest。 |

## 当前计划

| 计划 | 状态 | 说明 |
| --- | --- | --- |
| [2026-07-22 Conditional GO 全面评审整改](2026-07-22-conditional-go-review-remediation.md) | 历史保留/已完成 | WI1–WI11 严格串行；每项 PR、合并、归档、关闭、分支清理和默认分支同步均有证据；不得启动新工单。 |
| [2026-07-24 Release Post-Merge Source Verification](2026-07-24-release-postmerge-source-verification.md) | 执行中 | 修复候选内容与合并后精确来源身份之间的发布门禁。 |

## 历史保留计划

下列计划已完成或属于专项历史记录，保留原文和关联证据：

- [2026-07-14 评审整改循环](2026-07-14-review-remediation-loop.md)
- [2026-07-14 SBOM 与 Trust](2026-07-14-supply-chain-sbom-trust.md)
- [2026-07-15 治理整改](2026-07-15-governance-remediation.md)
- [2026-07-15 Supply Chain Evidence](2026-07-15-supply-chain-evidence.md)
- [2026-07-16 Archive History Threshold](2026-07-16-decouple-archive-history-threshold.md)
- [2026-07-20 全面评审整改（修订版）](2026-07-20-comprehensive-review-remediation.md) — 已被 2026-07-21 计划替代，保留审计历史。
- [2026-07-21 最新评审整改](2026-07-21-review-remediation.md) — 工单 1–17 已完成，PR #168 合并，上一版已发布，最后工单已关闭。
- [2026-07-21 Bootstrap Adoption 评审整改](2026-07-21-bootstrap-adoption-review-remediation.md) — WI01–WI15 已完成，PR #172–#186 合并，上一版已发布，保留完整审计证据。
- [2026-07-22 Project Calibration and Update Recalibration](2026-07-22-project-calibration-recalibration.md) — 已完成并压缩为 archive-backed closure index。
- [2026-07-22 Installed Lifecycle Management 评审整改](2026-07-22-installed-lifecycle-review-remediation.md) — 工单 1–16 已完成并压缩为 archive-backed closure index。
- [2026-07-22 AI Cockpit Governance Hardening](2026-07-22-ai-cockpit-governance-hardening.md) — 已完成并压缩为 archive-backed closure index。

相邻的 `../specs/` 属于独立设计证据。计划压缩或删除必须由 Contract
声明 scope，先完成引用扫描，并在 Summary 记录权威 archive 与 Git 恢复路径。
