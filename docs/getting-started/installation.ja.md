---
author: Ray
title: "インストール"
description: AI Cockpit を既存リポジトリへ導入するための日本語ガイド。
keywords:
  - ai-cockpit
  - installation
  - quick-start
---

# インストール

現在の能力と計画中の能力の境界は [Capability Truth Matrix](../reference/capability-truth-matrix.md) で確認できます。Runtime の導入だけでは校正は完了しません。現在の `configure_ai_cockpit` は Project Profile の提案を生成・検証し、中断・再開できる 10 Stage セッションと Candidate 有効化も実装済みですが、導入先での実行と人による確認が必要です。

AI Cockpit は、既存リポジトリへ公開済みリリースを導入します。まず [日本語 README](../../README.ja.md) のクイックインストールを実行し、その後このページで導入状態を確認してください。詳細な英語手順は [Installation](installation.md) を参照してください。

## 導入の流れ

1. **事前確認:** Git の作業ツリーが clean で、初回コミット、Python 3.10 以上、GNU Make が利用できることを確認します。
2. **インストール:** 対象プロジェクトに合う stack preset を選びます。導入先のリモート既定ブランチから作業ブランチを作成し、テンプレートの公開 release tag `v0.5.40` を使います。
3. **Adoption:** 生成された `adopt_ai_cockpit` Work Item を finish し、status を確認します。
4. **キャリブレーション:** Project Profile と Guard の提案をレビューし、プロジェクト固有の品質コマンドを設定します。
5. **検証:** `make check-ai-adoption-ready`、`make ai-cockpit-quality`、`make check-ai-status-consistency` を実行します。

## 事前確認

```sh
git status --short
git rev-parse --is-inside-work-tree
git rev-list --count HEAD
python3 --version
command -v make
```

作業ツリーが汚れている場合や初回コミットがない場合、インストーラーは fail closed します。まず原因を解消してから再実行してください。

## 導入後

```sh
make ai-onboard
make check-ai-adoption-ready
make ai-cockpit-quality
make check-ai-status-consistency
```

導入は実行系の配置で完了します。Project Profile、Guard、品質コマンド、CI の本番適合は、別の `configure_ai_cockpit` Work Item で人が確認します。設定後は [最初の Work Item](first-work-item.ja.md) に進んでください。
