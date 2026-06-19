---
author: Ray
title: "AI Cockpit"
description: Codex、Gemini、Claude、Cursor、Antigravity などの AI コーディングエージェント向けの、対象アプリケーション言語に依存しない変更管理テンプレート。
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

AI が生成した変更を、範囲を定めた独立のレビューなしに受け入れるべきではありません。

AI Cockpit は書き込み後の差分を検証する変更管理ワークフローであり、ファイルシステムの権限制御やセキュリティサンドボックスではありません。

AI Cockpit は、AI コーディングエージェント向けの変更管理基盤です。

AI 支援開発に軽量なレビューワークフローを追加します。

![AI Cockpit demo](docs/assets/ai-cockpit-demo.gif)

**AI が 37 ファイルを変更した。Cockpit がマージを止めた。**

AI Cockpit は、AI が生成した変更の範囲を制限し、レビューと監査を可能にします。

私は、AI が無関係なファイルを書き換え、完了済みの作業を戻し、レビュー要件をすり抜ける場面を何度も見ました。そこで、変更範囲（scope）、検証（checks）、変更概要（summary）、状態（status）を中心とした小さな変更管理ワークフローを作りました。

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

## 最新の公開ランタイムをインストール

```sh
RELEASE_TAG="$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/release.json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["releaseTag"])' 2>/dev/null || git ls-remote --tags --refs https://github.com/xinglun/ai-cockpit-template.git 'v*' | python3 -c 'import re,sys; tags=[m.group(1) for line in sys.stdin for m in [re.search(r"refs/tags/(v\d+\.\d+\.\d+)$", line)] if m]; print(max(tags, key=lambda tag: tuple(map(int, tag[1:].split(".")))))')"
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL "https://raw.githubusercontent.com/xinglun/ai-cockpit-template/${RELEASE_TAG}/install.sh" -o "$INSTALLER"
AI_COCKPIT_TEMPLATE_REF="$RELEASE_TAG" sh "$INSTALLER" --stack rust --update-makefile
```

このコマンドは公開済みの `release.json` を優先し、メタデータ移行中にファイルが存在しない場合は、公開済みのセマンティックバージョンタグから最新のものを選びます。その後、解決したタグのインストーラーのみをダウンロードして実行します。公開版の機能はソースツリーより遅れる場合があるため、初回導入 PR を作成する前に[インストール手順](docs/installation.md)を確認してください。

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
| Scope Guard | 宣言された変更範囲外の差分を検出し、完了・アーカイブ・マージのゲート通過を防ぐ。 |
| Backtrack Guard | 保護対象のテスト、スナップショット、Work Item 記録の削除を検出し、設定済みゲートの通過を防ぐ。 |
| Coverage Guard | 対応するテスト変更がない本番コード変更を検出し、設定済みゲートの通過を防ぐ。 |
| Agent Risk Guard | プロンプト上の指示だけでは強制力を持たないリスク、作業途中の逸脱、不明点を残した完了申告に対する必須ゲート。 |
| AI Review Policy | ガバナンスや CI の変更について、レビュー時の注視点を Change Summary に明記するよう促す（報告のみ）。 |
| Checkpoint | 作業途中の整合性スナップショット。完了前に変更範囲の逸脱を検出する。 |
| Status Consistency Guard | `current_status.md` が現在作業中の Work Item と一致するか検証する。 |
| Change Summary | 変更内容、検証結果、残るリスクを記録する。 |
| Cockpit Status | 現在の AI タスク状態を生成ビューで表示する。 |
| Finish Flow | チェック通過後にのみ Work Item をアーカイブする。 |

## 信頼モデル

- `ai-start` は `baseCommit` と開始前から変更済みのパス、その内容のフィンガープリントを記録する。
- Contract v2 は `.ai/cockpit/checks.yaml` に登録された check ID のみ参照でき、任意コマンドを指定できない。
- `ai-finish` はチェック ID、終了コード、実行コミット、Contract ハッシュ、コマンドハッシュ、機密情報を除去した出力要約を記録する。これは構造化記録であり暗号学的証明ではない。
- インストーラーは同じ PR 検証スクリプトと Make ターゲットを配布する。Work Item のアーカイブ後、CI で `make check-ai-pr AI_BASE_COMMIT=<merge-base>` を実行する。
- 除外対象でない各 PR パスは、同じ Contract と Summary の組において、変更範囲と `changedFiles` の両方に含まれる必要がある。
- 制限対象・破壊的変更の承認は、Contract 内の自己申告型ワークフロー記録である。信頼できる人間の承認には CODEOWNERS、保護された CI 環境、またはプラットフォームの ID イベントを使用する。
- AI Cockpit は誤操作と作業途中の逸脱を抑える仕組みであり、悪意ある AI エージェントに対するセキュリティサンドボックスではない。プロジェクトテストまたは `make quality` は独立した CI 必須チェックとして実行する。

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
Codex、Gemini、Claude、Cursor、Antigravity、およびその他の AI コーディングエージェント
```

スタック:

```text
generic, rust, flutter, typescript, python, go, java, android, kotlin, swift, ruby, php, csharp
```

互換性レベル:

<!-- stack-tiers: verified=python,go,rust,typescript; preset-only=generic,flutter,java,android,kotlin,swift,ruby,php,csharp -->

- **CI 検証済み:** `python`、`go`、`rust`、`typescript` は最小プロジェクトを生成し、`make quality` を実行します。
- **プリセットのみ:** `generic`、`flutter`、`java`、`android`、`kotlin`、`swift`、`ruby`、`php`、`csharp` はコマンドの出発点を提供しますが、実プロジェクトを使った CI 証跡はまだありません。`generic` は設定が完了するまで意図的に失敗します。
- **未対応の実行環境:** ネイティブ Windows シェル。WSL または別の POSIX 環境を使用してください。

スタックプリセットは、カスタマイズを前提とした出発点であり、依存ツールをインストールするものではありません。対象プロジェクトには、フォーマッター、テストランナー、SDK、ビルドプラグインがあらかじめ必要です。たとえば Java と Android は Gradle Wrapper と Spotless の設定、Python は Ruff と pytest を前提とします。`examples/` は一部のスタックのみを扱い、すべてのプリセットには対応していません。

ガバナンス実行系は対象言語に依存しませんが、スタックプリセットと既定のガード対象パスは、あらゆるフレームワークへの完全対応を意味しません。CI の必須チェックにする前に、対象リポジトリに合わせて `Makefile.ai.stack` と `.ai/guards/coverage_policy.yaml` を調整してください。

インストールで完了するのはガバナンス実行系の配置であり、本番運用向けの適合確認ではありません。品質コマンド、Coverage 対象パス、PR CI を設定した後、Coverage policy の `adoptionReviewed` を `true` に変更し、`make check-ai-adoption-ready` を実行してください。これは静的な設定完全性の検査であり、プロジェクトコマンドの有効性を証明するものではありません。CI では `make quality` と `check-ai-pr` の成功を別途必須にしてください。

固定済みの公開版には、現在のソースツリーにある初回導入用の監査フローがまだ含まれていません。AI Cockpit を導入する PR 自体に `check-ai-pr` を適用する場合は、先にインストールガイドのバージョン境界を確認してください。

## 動作環境要件

- Python 3.10 以上。
- merge-base および three-dot diff (`...`) をサポートする Git 環境。
- POSIX 準拠のシェルおよび GNU Make 実行環境。
- Linux および macOS は、ローカル実行および CI 用として公式にサポートされています。ネイティブの Windows シェルはサポートされていないため、WSL (Windows Subsystem for Linux) または他の POSIX ターミナルで実行してください。

リポジトリの `make quality` は、スクリプトカバレッジ 60% を下限とする全テスト、`scripts/` と `tests/` への Ruff、型注釈を整備した中核ツール群への Mypy、中・高重要度を対象とする Bandit、Python コンパイル、差分検査、ドキュメント整合性検査を実行します。Mypy の対象は意図的に限定しており、包括的な除外を追加せず段階的に拡大します。

## 詳細ドキュメント

- [インストール](docs/installation.md)
- [概要・コンセプトガイド](docs/overview.ja.md)
- [フィールド解説書](docs/contract-fields.md)
- [設定](docs/configuration.md)
- [アーキテクチャ](docs/architecture.md)
- [設計思想](docs/design-philosophy.md)
- [ケーススタディ: AI rollback corruption](docs/case-study-ai-rollback-corruption.md)
- [ローンチ用コピー](docs/launch.md)
- [推奨される GitHub Topics](docs/topics.md)
- [各言語のサンプル](examples/)
