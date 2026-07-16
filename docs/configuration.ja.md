---
author: Ray
title: "設定"
description: AI Cockpit の stack preset、Project Profile、Guard を設定する日本語ガイド。
keywords:
  - ai-cockpit
  - configuration
  - guards
---

# 設定

AI Cockpit のインストールは汎用の実行系を配置します。実際のプロジェクトで利用するには、stack preset、Project Profile、Guard、品質コマンドを調整してください。詳細な一覧は [Configuration](configuration.md) を参照してください。

## 基本方針

- `generic` はプロジェクト固有の品質コマンドを設定するまで fail closed です。
- stack preset は依存ツールをインストールしません。対象プロジェクトの SDK、フォーマッター、テストランナーを先に用意します。
- Project Profile と Guard は別の `configure_ai_cockpit` Work Item で管理します。
- Coverage の境界が不明な場合は、まず `reportOnly: true` で確認し、レビュー後に blocking へ移行します。

## 確認コマンド

```sh
make cockpit-doctor
make cockpit-calibrate
make check-ai-project-profile
make check-ai-guard-calibration
make ai-cockpit-quality
```

提案された設定をそのまま承認せず、検出事実、境界、未解決事項、品質コマンドを人がレビューしてください。
