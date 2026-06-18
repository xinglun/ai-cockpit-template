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
| Backtrack Guard | 保護対象のテスト、snapshot、Work Item 記録の削除をデフォルトでブロックする。 |
| Coverage Guard | 対応するテスト変更がない設定済み production code の変更をデフォルトでブロックする。 |
| Agent Risk Guard | prompt-is-advice、mid-task ドリフト、unknown-overclaim リスクに対するハードゲート。 |
| AI Review Policy | ガバナンス・ CI 変更のレビューフォーカスを Change Summary に明記するよう促す（報告のみ）。 |
| Checkpoint | mid-task 整合性スナップショット。完了前に scope ドリフトを検知する。 |
| Status Consistency Guard | `current_status.md` が現在の active Work Item 集合と一致するか検証する。 |
| Change Summary | 変更内容、検証結果、残るリスクを記録する。 |
| Cockpit Status | 現在の AI タスク状態を生成ビューで表示する。 |
| Finish Flow | チェック通過後にのみ Work Item を archive する。 |

## 信頼モデル

- `ai-start` は `baseCommit` と開始前の dirty path の内容 fingerprint を記録する。
- Contract v2 は `.ai/cockpit/checks.yaml` に登録された check ID のみ参照でき、任意コマンドを指定できない。
- `ai-finish` は check ID、終了コード、実行 commit、Contract hash、command hash、redact 済み出力要約を記録する。これは構造化記録であり暗号学的証明ではない。
- installer は同じ PR validator と Make target を配布する。Work Item archive 後、CI で `make check-ai-pr AI_BASE_COMMIT=<merge-base>` を実行する。
- 非 exempt の各 PR path は、同じ Contract/Summary pair の scope と `changedFiles` の両方に属する必要がある。
- restricted/destructive approval は Contract 内の自己申告型 workflow record である。信頼できる人間承認には CODEOWNERS、protected CI environment、platform identity event を使用する。
- AI Cockpit は誤操作と process drift を抑える仕組みであり、悪意ある agent に対する security sandbox ではない。project test または `make quality` は独立した required CI check として実行する。

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

## 動作環境要件

- Python 3.10 以上。
- merge-base および three-dot デイフ (`...`) をサポートする Git 環境。
- POSIX 準拠のシェルおよび GNU Make 実行環境。
- Linux および macOS は、ローカル実行および CI 用として公式にサポートされています。ネイティブの Windows シェルはサポートされていないため、WSL (Windows Subsystem for Linux) または他の POSIX ターミナルで実行してください。

## 詳細ドキュメント

- [インストール](docs/installation.md)
- [概要・コンセプト導読](docs/overview.ja.md)
- [フィールド解説書](docs/contract-fields.md)
- [設定](docs/configuration.md)
- [アーキテクチャ](docs/architecture.md)
- [設計思想](docs/design-philosophy.md)
- [ケーススタディ: AI rollback corruption](docs/case-study-ai-rollback-corruption.md)
- [ローンチ用コピー](docs/launch.md)
- [推奨される GitHub Topics](docs/topics.md)
- [各言語のサンプル](examples/)
