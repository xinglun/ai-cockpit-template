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

本目录保存可审计的执行计划。完成计划保留，用于追溯 Work Item、PR、验证结果和发布证据。

## 保留规则

| 分类 | 处理方式 |
| --- | --- |
| 当前执行 | 保留原文，标注执行中并链接 Work Item。 |
| 已完成/需审计 | 保留原文，补充完成状态、PR/发布证据和归档位置。 |
| 已替代/历史专项 | 保留原文，标注替代关系；删除必须另立工单并先完成链接扫描。 |

## 当前计划

| 计划 | 状态 | 说明 |
| --- | --- | --- |
| 无 | 已完成 | 最后一个计划清理工单已关闭；后续整改必须另立计划和 Work Item。 |

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

相邻的 `../specs/` 属于独立设计证据，不随计划清理删除。
