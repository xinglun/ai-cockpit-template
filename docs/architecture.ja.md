---
author: Ray
title: "アーキテクチャ"
description: AI Cockpit の証拠ガバナンスとリポジトリ境界を説明する日本語ガイド。
keywords:
  - ai-cockpit
  - architecture
  - governance
---

# アーキテクチャ

AI Cockpit は AI 支援開発のための Repository Governance Layer です。Agent Runtime、Workflow Engine、Security Sandbox ではありません。詳細な英語リファレンスは [Architecture](architecture.md) を参照してください。

## 証拠の流れ

```text
Intent → Contract → Implementation → Verification → Summary → Cockpit Status → Human Decision
```

- **Intent:** なぜ作業を行うのか、制約、根拠を記録します。
- **Contract:** 変更範囲、除外範囲、受入条件、検証を作業前に宣言します。
- **Verification:** 登録済みの Make ターゲットで変更を検証します。
- **Summary:** 変更、証拠、残存リスク、レビュー準備を記録します。
- **Cockpit Status:** Summary の証拠をレビュー判断向けに圧縮します。

## 境界

Native Governance Evidence は Contract、Summary、Status など AI Cockpit 自身が管理する証拠です。テスト、カバレッジ、SBOM、脆弱性スキャンは Delegated Domain Evidence であり、専門ツールが生成します。
