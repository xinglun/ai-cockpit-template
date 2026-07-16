---
author: Ray
title: "ガバナンス複雑度"
description: AI Cockpit のリポジトリ複雑度レポートと確認方法を説明する日本語リファレンス。
keywords:
  - ai-cockpit
  - governance
  - complexity
---

# ガバナンス複雑度

ガバナンス複雑度チェックは、リポジトリの規模と AI Cockpit の監査証拠量を観測します。現在の Work Item を判断するための補助情報であり、履歴の増加だけを理由に過去の証拠を削除するための機能ではありません。

## 観測する指標

- tracked file 数
- Python 行数
- Markdown 行数
- アーカイブ済み Contract/Summary の数
- アーカイブインデックスのエントリ数と整合性

アーカイブ数は不変の履歴として観測されます。累積履歴の増加だけで、無関係な新しい Work Item をブロックしない設計です。ファイル所有権、Contract/Summary の対応、インデックスの整合性は引き続き blocking の検査です。

## 実行

```sh
make check-governance-complexity
```

レポートが示す数値はリポジトリの現在状態のスナップショットです。閾値に関する警告が出た場合は、`.ai/guards/` のポリシーと、計測対象が意図した範囲かを確認してください。

## レビュー時の注意

- アーカイブ済み Contract/Summary は監査履歴として保持する。
- 現在の PR に含まれるアーカイブ証拠の所有権は `make check-ai-pr AI_BASE_COMMIT=<merge-base>` で確認する。
- 複雑度の閾値を緩める場合は、何を観測値にし、何を blocking に残すかを記録する。
- 履歴の圧縮や削除は、独立した提案と人間のレビューなしに実施しない。
