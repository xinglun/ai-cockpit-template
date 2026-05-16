---
author: Ray
description: Codex、Gemini、Antigravity などの AI コーディングエージェント向けの言語非依存 AI ガバナンステンプレート。
keywords:
  - ai-agents
  - codex
  - gemini
  - antigravity
  - agentic-coding
  - developer-tools
  - governance
  - template
  - automation
  - ci
---

# ai-cockpit-template

[English](README.md) | [中文](README.zh-CN.md)

`ai-cockpit-template` は、Codex、Gemini、Antigravity などのコーディングエージェントを使う開発チーム向けの、言語非依存な AI ガバナンス足場です。AI によるコード変更の前にタスク境界を定義し、変更範囲を制御し、検証を要求し、変更内容を要約し、監査可能な記録を残します。

## 対象者

- 本番コードベースに AI コーディングエージェントを導入するチーム。
- AI が生成した diff を、境界付き・レビュー可能・ロールバック可能にしたいメンテナー。
- Rust、Flutter、TypeScript、Python、または複数言語のコードベースで同じ AI ワークフローを使いたいエンジニア。
- サービス、データベース、専用ランタイムを増やさずに軽量なガバナンスを導入したい組織。

## 解決する問題

AI エージェントは高速に作業できますが、依頼範囲を外れたり、テストを削除したり、無関係なファイルを書き換えたり、検証を省略したり、レビュー担当者に変更意図が伝わらない diff を残すことがあります。このテンプレートは、各 AI タスクを Work Item として明示し、scope、required checks、summary を機械的に確認できる形にします。

## 設計思想

人類文明は、システムを作り、そのシステムを進化させ、やがて複雑性が人間の直接的な制御を超える段階に到達します。そのとき必要になるのは複雑性の圧縮です。内部プロセスは black box になり、cockpit は人間が判断するために必要な状態だけを返します。

このフレームワークは、私が今回の AI 開発課題から出発して設計したものです。発想そのものは新しくありませんし、航空システムを真似たものでもありません。私が同じ制御問題を真剣に解いた結果、自然に同じ形になったということです。

強いシステムは必ず制御されます。作業計画、境界、検証、記録、状態表示。AI 開発にも同じ層が必要です。

| AI 開発の課題 | 必要な制御層 | 航空システムの類比 |
| --- | --- | --- |
| 作業計画が曖昧 | Work Item Contract | 飛行計画 |
| 変更範囲が不明 | Scope Guard | 管制区域 |
| 検証が不十分 | Required checks | 計器確認 |
| 記録が残らない | Change Summary と archive | ブラックボックス |
| 状態が見えない | Cockpit Status | コックピット |

外部の仕組みを持ち込んだのではなく、今回の問題を解くために必要な要素を積み重ねた結果、自然に航空システムに似た構造になりました。

## 提供するもの

- Work Item Contract: AI がファイルを変更する前のタスク境界。
- Scope Guard: 宣言された scope 外の変更を防ぐ。
- Backtrack Guard: テスト、snapshot、Work Item 記録の未宣言削除を報告する。
- Coverage Guard: テスト変更を伴わない production code の変更を報告する。
- Change Summary: 変更内容、検証結果、残るリスクを記録する。
- Cockpit Status: 現在の AI タスク状態を一画面で見られるよう生成する。
- Finish Flow: チェック通過後にのみ Work Item を archive する。
- Installer: 既存リポジトリへ非破壊的に AI Cockpit を追加する。

## ディレクトリ構成

```text
.ai/
  cockpit/
    README.md
    checks.yaml
    current_status.md
  guards/
    backtrack_policy.yaml
    cockpit_status_policy.yaml
    coverage_policy.yaml
    file_boundary.yaml
    file_ownership.yaml
    scope_policy.yaml
    summary_policy.yaml
  work-items/
    _templates/
      work_item_contract.example.json
      work_item_summary.example.json
    active/
    archive/
examples/
  flutter/
  rust/
  typescript/
scripts/
  ai_*.py
  install_ai_cockpit.py
templates/
  make/
    Makefile.ai
  stacks/
    flutter.mk
    generic.mk
    python.mk
    rust.mk
    typescript.mk
install.sh
Makefile
AGENTS.md
GEMINI.md
```

## クイックスタート

このリポジトリは GitHub template として新規プロジェクトに使えます。既存プロジェクトへインストールすることもできます。

### 既存プロジェクトへインストール

ローカル clone からインストール:

```sh
/path/to/ai-cockpit-template/install.sh --stack rust
```

リモートから一行でインストール:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

より安全な二段階インストール:

```sh
curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh -o install-ai-cockpit.sh
sh install-ai-cockpit.sh --stack rust
```

対応 stack preset:

```text
generic
rust
flutter
typescript
python
```

インストーラーのオプション:

```text
--dry-run          ファイルを書き込まず、実行予定の操作だけ表示する。
--force            既存の AI Cockpit ファイルを上書きする。
--with-examples    examples/ を対象リポジトリにコピーする。
--update-makefile  対象 Makefile に "include Makefile.ai" を追記する。
```

デフォルトのインストールは保守的です:

- 既存 Makefile を直接書き換えず、`Makefile.ai` と `Makefile.ai.stack` を作成します。
- 既存の `AGENTS.md` と `GEMINI.md` には AI Cockpit section を追記します。
- 既存ファイルは `--force` がない限りスキップします。

`--update-makefile` を使わなかった場合は、プロジェクトの Makefile に次を追加してください:

```make
include Makefile.ai
```

### Work Item を開始する

Work Item を作成:

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

生成された Contract を編集:

```text
.ai/work-items/active/example_change.contract.json
```

実際のコードやドキュメント変更は、Contract の `scope` 内だけで行います。

Summary を更新:

```text
.ai/work-items/active/example_change.summary.json
```

finish flow を実行:

```sh
make ai-finish TASK=example_change
```

Finish flow は AI チェックを実行し、`.ai/cockpit/current_status.md` を生成し、状態を検証し、プロジェクト品質チェックを実行し、通過後に Contract と Summary を archive します。

## プロジェクトチェックのカスタマイズ

インストーラーは `Makefile.ai.stack` を作成します。Stack preset は次の変数でコマンドを設定します:

```make
PROJECT_FORMAT_CHECK = printf '%s\n' 'No formatter configured.'
PROJECT_TEST = printf '%s\n' 'No test command configured.'
PROJECT_LINT = printf '%s\n' 'No linter configured.'
```

Rust:

```make
PROJECT_FORMAT_CHECK = cargo fmt --all -- --check
PROJECT_TEST = cargo test
PROJECT_LINT = cargo clippy --all-targets -- -D warnings
```

Flutter:

```make
PROJECT_FORMAT_CHECK = dart format --set-exit-if-changed .
PROJECT_TEST = flutter test
PROJECT_LINT = flutter analyze
```

TypeScript:

```make
PROJECT_FORMAT_CHECK = npm run format:check
PROJECT_TEST = npm test
PROJECT_LINT = npm run lint
```

Python:

```make
PROJECT_FORMAT_CHECK = python3 -m ruff format --check .
PROJECT_TEST = python3 -m pytest
PROJECT_LINT = python3 -m ruff check .
```

`.ai/cockpit/checks.yaml` を更新すると、エージェントがタスクごとに選ぶべきチェックも調整できます。

## Guard 設定

- `.ai/guards/file_ownership.yaml` は restricted / forbidden な AI 書き込みを制御します。
- `.ai/guards/file_boundary.yaml` は generated / runtime artifact がコード diff に混入するのを防ぎます。
- `.ai/guards/coverage_policy.yaml` は production path と test path の pattern を定義します。
- `.ai/guards/scope_policy.yaml` は常に許可する path と任意の dependency scope ルールを定義します。

Guard YAML parser は小さな YAML subset のみを扱うため、スクリプトは Python 標準ライブラリだけで動作します。

## バージョン固定インストール

tag を指定すると再現可能なインストールにできます:

```sh
AI_COCKPIT_TEMPLATE_REF=v0.1.1 \
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust
```

## テンプレート方針

このリポジトリには、業務ロジック、個人パス、実 API key、GitHub secrets、組織固有の runtime config を追加しないでください。テンプレートは汎用に保ち、実プロジェクト固有の方針は導入先リポジトリに置いてください。
