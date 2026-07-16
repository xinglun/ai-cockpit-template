---
author: Ray
title: "導入先プロジェクトの設定"
description: AI Cockpit を導入したプロジェクトで必要な設定を確認する日本語ガイド。
keywords:
  - ai-cockpit
  - adopter
  - configuration
---

# 導入先プロジェクトの設定

インストール後は、テンプレートの既定値をプロジェクト固有の境界へ適合させます。対応する英語版は [Adopter Configuration](adopter-configuration.md) です。

## 必須確認

- `.github/CODEOWNERS` の所有者を実際のレビュー担当へ置き換える。
- `SECURITY.md` の脆弱性報告先、対応範囲、開示方針をプロジェクトの方針へ置き換える。
- `.ai/project_profile.yaml` に承認済みのリポジトリ事実、品質コマンド、カバレッジ境界を記録する。
- `.ai/guards/` と Project Profile の境界が一致していることを確認する。
- CI で `make check-ai-pr` と `make ai-cockpit-quality` を実行する。

## 作業単位

インストールの `adopt_ai_cockpit` と、設定の `configure_ai_cockpit` は別の Work Item と専用ブランチに分けます。設定 Contract の scope には実際に変更するパスだけを記載し、`make cockpit-doctor` と `make cockpit-calibrate` の提案を人が確認してから Profile を確定してください。

```sh
make ai-start TASK=configure_ai_cockpit TITLE="Configure AI Cockpit for this project" MODE=code
make ai-onboard
make check-ai-adoption-ready
make ai-cockpit-quality
```

このチェックが成功しても、選択した品質コマンドが十分かどうかを自動的に証明するものではありません。プロジェクト責任者がレビューしてから本番ゲートへ昇格させてください。
