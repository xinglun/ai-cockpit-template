---
author: Ray
title: "最初の Work Item"
description: AI Cockpit 導入後に最初の管理対象タスクを実行する日本語ガイド。
keywords:
  - ai-cockpit
  - work-item
  - verification
---

# 最初の Work Item

導入と設定の検証が成功したら、最初の管理対象タスクを開始します。完全な英語手順は [First Work Item](first-work-item.md) を参照してください。

## 開始

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

生成された Contract を編集し、`scope`、`outOfScope`、`sources`、`acceptance`、`verification` を実際のタスクに合わせます。`unknowns` を解消し、`agentCapability` と `executionDecision.status` を確認してから、次を実行します。

```sh
make ai-checkpoint CONTRACT=.ai/work-items/active/example_change.contract.json STAGE=before_edit
```

Preflight が `needs_human_confirmation` または `not_ready` を返した場合は、実装を止めてレビュー結果を人へ報告します。

## 完了

変更後は Summary に変更ファイル、検証結果、残存リスク、レビュー注視点を記録します。

```sh
make ai-checkpoint CONTRACT=.ai/work-items/active/example_change.contract.json SUMMARY=.ai/work-items/active/example_change.summary.json STAGE=before_finish
make ai-finish TASK=example_change
```

`ai-finish` は Contract の検証、Summary 更新、Cockpit Status 生成、アーカイブを行います。PR が merge されるまで作業ブランチを削除せず、merge 後に承認を得て `make ai-close-work-item TASK=example_change` を実行してください。
