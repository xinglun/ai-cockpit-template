---
author: Ray
title: "Glossary"
description: AI Cockpit の主要用語とアーキテクチャ境界の定義。
---

# AI Cockpit 用語集

この文書は、このリポジトリで使用するガバナンス用語を定義します。実装前に確認し、Contract、Summary、ドキュメント、およびコードで一貫した名称を使用してください。

## 主要用語

| 用語 | 定義 |
| --- | --- |
| Intent | タスクが存在する理由を宣言する一級ガバナンスオブジェクト。problem（問題の詳細）、constraints（制約）、rationale（根拠）などを含む（全フィールドは任意）。Contract に先行し、Contract を駆動する。 |
| Work Item Contract | 変更前に scope、outOfScope、sources、acceptance、verification、および実行可否を宣言する JSON 記録。Intent に基づいて作成される。 |
| AI Change Summary | 変更内容、検証結果、ガイドライン準拠、残存リスク、および Intent Alignment を記録する JSON 記録。Intent への整合性を検証する。 |
| Intent Alignment | Summary における Intent 達成度の検証。problemResolved、constraintsRespected、nonGoalsAvoided、rationaleValidated などを含む。 |
| Governance Loop | Intent → Contract → Implementation → Verification → Summary (Intent Alignment) の完全なガバナンス閉ループ。 |
| Active Work Item | `.ai/work-items/active/` に Contract と Summary の組が存在する、作業中の項目。 |
| Archived Work Item | 検証後に `.ai/work-items/archive/` へ移動された Contract と Summary の監査記録。 |
| Scope Guard | 実際の差分が Contract の scope 内かを検証する仕組み。 |
| Check ID | `.ai/cockpit/checks.yaml` に登録された、Contract から参照可能な検証項目の識別子。 |
| Cockpit Status | Active Work Item の状態を示す生成ファイル。手動では編集しない。 |
| Repository Governance Layer | AI Cockpit の役割定義。Agent Runtime や Workflow Engine ではなく、リポジトリレベルのガバナンス、コンテキスト、検証、監査可能性を提供する。 |

## アーキテクチャ境界

- `scripts/`: Python 標準ライブラリを中心とするガバナンス実行系。
- `.ai/cockpit/`: check catalog、生成 status、および workflow の説明。
- `.ai/guards/`: scope、ownership、boundary、backtrack、coverage、および review policy の設定。
- `templates/`: インストール先へ配布するルール、glossary、および stack preset。
- `examples/`: 一部の stack 向け設定例。全 preset の動作保証一覧ではない。
