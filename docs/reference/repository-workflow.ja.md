---
author: Ray
title: "リポジトリワークフロー"
description: Work Item、ブランチ、PR、アーカイブの標準手順を説明する日本語リファレンス。
keywords:
  - ai-cockpit
  - repository-workflow
  - work-item
  - pull-request
---

# リポジトリワークフロー

標準のレビュー単位は、1 Work Item、1 専用ブランチ、1 Pull/Merge Request です。無関係な作業を同じ Contract や PR に混ぜません。

## 開始からレビューまで

1. テンプレートリポジトリでは最新の `origin/main`、導入先では発見したリモート既定ブランチの最新コミットを取得する。
2. 専用ブランチを作成し、`baseRemote`、`baseBranch`、`baseCommit` を Contract に記録する。
3. `make ai-start TASK=<task> TITLE="..." MODE=code` で Work Item を作成する。
4. Contract の scope、outOfScope、sources、acceptance、verification、unknowns、executionDecision を確定する。
5. `before_edit` checkpoint 後に宣言範囲だけを変更する。
6. Summary を更新し、`before_finish` checkpoint を記録して `make ai-finish TASK=<task>` を実行する。
7. archived Contract/Summary と生成 Status を確認し、ブランチを push して PR を作成する。

## 禁止されるショートカット

- PR 前に feature branch をローカル `main` へ merge しない。
- PR が merge される前に Work Item branch を削除しない。
- 自動 merge や、`ai-close-work-item` が branch ownership を確認する前の自動 branch 削除を有効にしない。
- Contract と Summary の片方だけを削除しない。

## 導入・アップグレード

導入とアップグレードは導入先プロジェクトの履歴に属します。移動中のテンプレートブランチではなく、公開済みテンプレート release tag を使用し、導入・設定・通常開発を別 Work Item に分けます。

## クローズ

PR が merge され、merged PR と archive 証拠が確認できた後に、明示的な承認を得て次を実行します。

```sh
make ai-close-work-item TASK=<task>
```

このコマンドは archived Contract/Summary、PR 所有権、base の fast-forward 同期、ローカル/リモート branch の削除、clean worktree、base と remote base の一致を検証します。どれかが失敗した場合は fail closed です。
