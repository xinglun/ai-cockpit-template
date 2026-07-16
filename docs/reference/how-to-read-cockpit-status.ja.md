---
author: Ray
title: "Cockpit Status の読み方"
description: 生成された current_status.md を読み、レビュー判断へつなげる日本語ガイド。
keywords:
  - ai-cockpit
  - cockpit-status
  - reviewer-guide
---

# Cockpit Status の読み方

このページは、生成された Cockpit Status を読み、状態からレビュー判断へ最短で到達するためのガイドです。対象読者はレビュアー、保守担当者、承認担当者です。実装を始める前は必ず最新の Preflight Review を確認してください。Cockpit Status はレビュー向けの表示であり、実装前の pause を置き換えません。

## 読む順序

1. active Work Item に表示される `Preflight Review`
2. `Recommendation`
3. `Decision Drivers`
4. `Governance Signals`
5. `Evidence`
6. Signals に表示される場合は `Scenario Coverage`

Preflight Review は Contract の証拠から実装準備度を導出します。既定では advisory ですが、コーディング開始前に表示します。

## Preflight Review の意味

| 状態 | 意味 |
| --- | --- |
| `ready` | 実装開始に十分な Contract 証拠があり、人間による確認 pause は不要。 |
| `needs_human_confirmation` | 利用できる証拠はあるが、弱い信号を実装前に人が確認する必要がある。 |
| `not_ready` | 実装を支える証拠が不足しているため、不足が解消されるまで停止する。 |

このレビューは AI の自信を示すものではありません。`intent`、`unknowns`、`sources`、`acceptance`、`scope`、`outOfScope`、`riskAssessment`、`scenarioCoverage`、`verification` などの既存 Contract 証拠から生成されます。

`notCodable: true`、`executionDecision.status` が `block` / `defer` / `needs_human_decision`、または `agentCapability` が実装・検証不可や人間判断を示す場合は、直ちに `not_ready` になります。

## Active Work Item がない場合

`no_active_work_item` は active Contract/Summary の組がない状態です。作業ツリーが変更されていないことを意味しません。ローカルの所有権は `make check-ai-diff-ownership`、PR の最終監査は `make check-ai-pr AI_BASE_COMMIT=<merge-base>` で確認します。

## Recommendation の意味

| Recommendation | 意味 |
| --- | --- |
| `ready_for_review` | 作業と証拠が揃い、正確性に集中してレビューできる。 |
| `ready_with_risks` | レビュー可能だが、記録された残存リスクの確認が必要。 |
| `needs_investigation` | 状態が不完全または曖昧で、人間による調査が必要。 |
| `blocked` | hard blocker があり、解消までレビューを停止する。 |

## 次に確認する項目

- `ready_for_review` なら `Decision Drivers` の注記を確認し、必要に応じて `Evidence` を読む。
- `ready_with_risks` なら最初に `Residual Risk` を読む。
- `needs_investigation` なら `Verification`、`Unknowns`、`Acceptance` を確認する。
- `blocked` なら `Decision Drivers` の blocker 解消を優先し、先へ進まない。
- `Scenario Coverage` が `incomplete` なら、Summary に残存リスク、follow-up、未検証シナリオの扱いが明示されているか確認する。
- Preflight が `needs_human_confirmation` または `not_ready` なら、Status が表示されていても実装を止めてユーザーへ報告する。

## 代表的な状態

```text
Recommendation: ready_for_review
Governance Signals:
- Intent: resolved
- Acceptance: complete
- Unknowns: resolved
- Verification: passed
- Guidelines: satisfied
- Checkpoints: complete
- Residual Risk: low
- Scenario Coverage: not_required
```

`ready_with_risks` は残存リスクを Summary に明記した場合にのみ使用します。検証不足や未解決の unknowns を隠すための肯定的な状態ではありません。
