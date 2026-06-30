---
author: Ray
title: "AI Cockpit"
description: AI Cockpit ワークスペース概要とワークフローガイド（日本語）。
keywords:
  - ai-cockpit
  - work-item-contract
  - scope-guard
  - change-summary
  - cockpit-status
---

# AI Cockpit

[English](README.md)

AI Cockpit は、エージェント型開発のための協調エンジニアリング環境です。Codex、Gemini、Claude、Cursor、Antigravity などのコーディングエージェントに、ファイル変更前の共通運用契約を提供します。

コックピットは言語非依存です。明示的なスコープ、委譲されたチェック、レビュー証跡、監査可能なタスク記録を通じて AI Change Governance を提供し、Makefile はプロジェクト固有のチェックを各リポジトリでカスタマイズ可能なコマンドへ委譲します。

## コアファイル

- `checks.yaml`: チェックカタログとプロジェクト固有コマンドの選択指針。
- `current_status.md`: アクティブ Work Item の生成済みステータスビュー。
- `.ai/work-items/active/*.contract.json`: 作業開始前のタスク境界。
- `.ai/work-items/active/*.summary.json`: 完了前の変更レポート。
- `.ai/guards/*.yaml`: ファイル所有権、境界、スコープ、バックトラック、カバレッジルール。

## フロー

1. `make ai-start TASK=<task> TITLE="..." MODE=code` で Work Item を作成する。
2. Contract の `scope`、`sources`、`acceptance`、`verification`、リスク評価、エージェント能力、実行判断を明確にする。
3. 宣言したスコープ内のみ実装する。
4. Summary に変更ファイル、チェック結果、リスク、レビュー準備、境界チェック、既知ギャップ、破壊的変更を記録する。
5. `make ai-finish TASK=<task>` を実行する。
6. 生成されたステータスとアーカイブ済み Contract/Summary をレビューする。

`unknowns` や `notCodable` は失敗ではなく有効な出力です。Summary は監査記録であると同時に協働の引き継ぎです。checkpoint は長いタスクのドリフトを防ぐための環境支援であり、単なる遵守項目ではありません。

`current_status.md` は生成物です。手編集しないでください。

## 初回導入のショートカット

インストール後の設定は、個別コマンドの羅列ではなく次の 3 フェーズに整理できます。

```sh
make ai-onboard              # 環境 → キャリブレーション → 導入準備
make ai-onboard PHASE=1      # 環境確認のみ
make ai-onboard PHASE=2      # キャリブレーションのみ
make ai-onboard PHASE=3      # 導入準備のみ
```

詳細なチェックリストは [導入準備ガイド](adoption.ja.md) を参照してください。

## ライフサイクルチェック

`make ai-start` は新しい skeleton 作成前にライフサイクル preflight を実行します。アクティブ Contract/Summary が不整合、複数 Work Item が同時アクティブ、`current_status.md` が実状態と不一致の場合は開始を拒否します。

`current_status.md` を生成または検証した後、Work Item を完了せずにライフサイクル状態だけ確認する場合は `make check-ai-status-consistency` を実行します。

アクティブ Work Item が 0 件、または 1 組の Contract/Summary ペアだけの場合、`make repair-ai-status` で `current_status.md` を再生成できます。不整合ファイルや複数アクティブ Work Item の修復は含みません。

## エージェントリスク制御

AI Cockpit はプロンプト指示をガイダンスとして扱い、強制力とはみなしません。リポジトリの安全性は、実際の Work Item と diff を検査するハードゲートから得られます。

既定テンプレートは 3 つの一般的なエージェントリスクを次の制御へ対応付けます。

- プロンプトは助言にすぎない: `make check-ai-agent-risk` が Contract の必須 AI ゲートが verification に含まれ、Summary で passed であることを検証する。
- 作業中のドリフト: `make ai-checkpoint` がスコープ、スコープ外ファイル、unknowns、acceptance、必須チェック状態、レビュー注視点、次アクション、checkpoint メタデータを表示する。
- 不確実性の過大主張: Contract 検証と Agent Risk Guard が unknowns または `notCodable` 状態で非 coding の execution decision を要求する。

Contract の `checkpointPolicy.requiredBeforeFinish` が true の場合、完了前に Summary の `checkpointEvidence` に checkpoint 使用を記録する。

## レビュー準備

Contract の readiness フィールドは、コーディング開始前にエージェントが実装と検証を実行できるかを記録します。Summary の readiness フィールドは残留リスク、期待レビュー注視点、境界チェック、ユーザー修正、既知ギャップ、未検証の主張を記録します。

このテンプレートを他リポジトリへコピーする場合、これらのフィールドは言語中立に保つ。

`.ai/guards/ai_review_policy.yaml` で宣言されたガバナンス機微パスについては `make check-ai-review-policy SUMMARY=<summary.json>` を実行する。このチェックは報告のみで、Summary に `reviewReadiness.expectedReviewFocus` があるかを記録する。

アーカイブ後、PR CI は `make check-ai-pr AI_BASE_COMMIT=<merge-base>` を実行する。インストール済み配布物にはこのターゲットと検証器が含まれる。PR diff 全体の非免除パスは、1 つの変更済みアーカイブペアによって共同所有されなければならない。Contract の scope 内かつ outOfScope 外であり、対応 Summary に報告されていること。

PR 証跡には Contract version 2 が必要である。version 1 はレガシー読み取り専用で、新規 PR 証跡として導入できない。Contract の承認フィールドは自己申告記録であり、人間 ID の証明ではない。信頼できる承認には保護されたプラットフォームレビューを使い、ガバナンス PR チェックとは独立してプロジェクトテストを実行する。
