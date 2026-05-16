---
author: Ray
title: "AI Cockpit"
description: Codex、Gemini、Claude、Cursor、Antigravity などの AI コーディングエージェント向けの言語非依存 AI ガバナンステンプレート。
keywords:
  - ai-agents
  - ai-agent
  - ai-workflow
  - code-review
  - llmops
  - ai-safety
  - codex
  - gemini
  - claude
  - cursor
  - antigravity
  - agentic-coding
  - developer-tools
  - developer-workflow
  - governance
  - template
  - automation
  - ci
---

# AI Cockpit

[English](README.md) | [中文](README.zh-CN.md)

AI コーディングエージェントは、次のようなことを起こし得ます。

- 無関係なファイルを書き換える
- テストを静かに削除する
- 検証を飛ばす
- レビュー担当者に意図を推測させる

AI エージェントにリポジトリ全体の root access を渡すべきではありません。

AI Cockpit は、coding agents のための AI Change Governance です。

AI 支援開発に軽量な AI review workflow を追加します。

![AI Cockpit demo](docs/assets/ai-cockpit-demo.gif)

**AI が 37 ファイルを変更した。Cockpit が merge を止めた。**

AI Cockpit は、AI が生成した変更を境界付き、レビュー可能、監査可能にします。

私は、AI が無関係なファイルを書き換え、完了済みの作業を戻し、レビュー期待をすり抜ける場面を何度も見ました。だから scope、checks、summary、status を中心にした小さな change-control workflow を作りました。

## 30 秒で理解する

Before:

```text
AI が 24 ファイルを変更した。
なぜ変更したのか誰も分からない。
テストが消えているかもしれない。
レビューは混乱から始まる。
```

After:

```text
タスク範囲が宣言されている。
チェックが強制される。
Summary が生成される。
Cockpit が更新される。
レビューは文脈から始まる。
```

## 3 分でインストール

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

ガバナンス付きの AI タスクを開始します。

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

チェックと監査記録付きで完了します。

```sh
make ai-finish TASK=example_change
```

## 仕組み

```text
Plan -> Scope -> Verify -> Summarize -> Status -> Archive
```

| 層 | 役割 |
| --- | --- |
| Work Item Contract | AI がファイルを変更する前にタスク境界を宣言する。 |
| Scope Guard | 宣言された scope 外の変更を防ぐ。 |
| Backtrack Guard | テスト、snapshot、Work Item 記録の未宣言削除を報告する。 |
| Coverage Guard | テスト変更を伴わない production code の変更を報告する。 |
| Change Summary | 変更内容、検証結果、残るリスクを記録する。 |
| Cockpit Status | 現在の AI タスク状態を生成ビューで表示する。 |
| Finish Flow | チェック通過後にのみ Work Item を archive する。 |

## 何を検出するか

```text
[BLOCKED]
Scope violation detected.

Unauthorized file modification:
- src/auth/payment.rs

Allowed scope:
- src/auth/session.rs
- tests/auth/session_test.rs
```

## 対応

エージェント:

```text
Codex, Gemini, Claude, Cursor, Antigravity, and other coding agents
```

スタック:

```text
generic, rust, flutter, typescript, python, go, java, kotlin, swift, ruby, php, csharp
```

## 詳細ドキュメント

- [インストール](docs/installation.md)
- [設定](docs/configuration.md)
- [アーキテクチャ](docs/architecture.md)
- [設計思想](docs/design-philosophy.md)
- [ケーススタディ: AI rollback corruption](docs/case-study-ai-rollback-corruption.md)
- [ローンチ用コピー](docs/launch.md)
- [推奨される GitHub Topics](docs/topics.md)
- [各言語のサンプル](examples/)
