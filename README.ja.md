---
author: Ray
title: "AI Cockpit"
description: Codex、Gemini、Claude、Cursor、Antigravity などの AI コーディングエージェント向けの、対象アプリケーション言語に依存しない協調エンジニアリング環境兼変更管理テンプレート。
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

AI Cockpit の製品境界は Repository Governance Layer であり、Agent Runtime、Workflow Engine、Security Sandbox ではありません。リポジトリ内の記録はレビューを支えますが、信頼できる ID、production 隔離、企業監査・コンプライアンス、配布基盤の証拠は外部管理です。

AI コーディングエージェントは、次のようなことを起こし得ます。

- 無関係なファイルを書き換える
- テストを静かに削除する
- 検証を飛ばす
- レビュー担当者に意図を推測させる

AI が生成した変更を、範囲を定めた独立のレビューなしに受け入れるべきではありません。重要なのは AI への信頼を最大化することではなく、証拠に基づいて依存、調査、人による介入、または停止を判断できることです。

**AI Cockpit は、証拠に基づくガバナンスによって、人と AI エージェントの調整された信頼を実現します。**

Calibrated trust（調整された信頼）とは、エージェントへの信頼を最大化することではありません。証拠が依存を支えるときにエージェントへ任せ、証拠がない、古い、矛盾している、または不十分なときに人が介入できるようにすることです。

## AI Cockpit とは

**AI Cockpit は AI アシスト型ソフトウェア開発のためのリポジトリガバナンスレイヤーです。** これは使命を実現するための具体的な製品境界です。

Agent Runtime **ではありません**。Workflow Engine **でもなく**、Security Sandbox **でもありません**。

哲学は **Evidence over Self-Declaration（自己申告より証拠）** です。メカニズムは **Evidence Governance** であり、AI Cockpit はガバナンス記録を作成し、委譲された証拠を評価し、その両方を人間の意思決定状態へ圧縮します。

AI Cockpit が提供するもの:

- **ガバナンス**: スコープ境界、検証要件、ポリシー執行
- **リポジトリコンテキスト**: 明示的なインテント、制約、アーキテクチャ知識
- **検証**: 宣言された契約に対する独立した変更検証
- **監査可能性**: 何が変更され、なぜ変更され、どのように検証されたかの完全な記録
- **インテント**: 何を実装すべきかだけでなく、なぜ作業が存在するかの一級表現

AI Cockpit は Claude Code、Codex、Cursor、Gemini CLI のようなエージェントを置き換えるものではありません。エージェントはモデルの能力とともに進化し続けます。**ガバナンスは安定であるべきです。**

AI Cockpit は書き込み後の差分を検証する変更管理ワークフローであり、ファイルシステムの権限制御やセキュリティサンドボックスではありません。

AI Cockpit は証拠を管理しますが、証拠を生成するツールを置き換えるものではありません。Native Governance Evidence / Delegated Domain Evidence の分類と Release の責任境界は [設計思想](docs/philosophy/design-philosophy.md) で定義します。

![AI Cockpit demo](docs/assets/ai-cockpit-demo.gif)

**AI が 37 ファイルを変更した。Cockpit がマージを止めた。**

AI Cockpit は、AI が生成した変更の範囲を制限し、レビューと監査を可能にします。

私は、AI が無関係なファイルを書き換え、完了済みの作業を戻し、レビュー要件をすり抜ける場面を何度も見ました。そこで、変更範囲（scope）、検証（checks）、変更概要（summary）、状態（status）を中心とした、明示的な契約を中核制御機構とするガバナンスレイヤーを構築しました。

## 30 秒で理解する

導入前：

```text
AI が 24 ファイルを変更した。
なぜ変更したのか誰も分からない。
テストが消えているかもしれない。
レビューは混乱から始まる。
```

導入後：

```text
タスク範囲が宣言されている。
チェックが強制される。
Summary が生成される。
Cockpit が更新される。
レビューは文脈から始まる。
```

<!-- install-prerequisites: python3.10,git-initial-commit,curl,gnu-make,posix -->

**前提条件:** POSIX シェルを利用できる Linux、macOS、または WSL、Python 3.10 以上、Git、curl、GNU Make、および 1 件以上のコミットがあるクリーンな Git リポジトリが必要です。選択したスタックのフォーマッター、テストランナー、SDK、ビルドプラグインも事前にインストールしてください。

バージョン履歴と能力の進化は、この短い入口ページではなく [ロードマップ](docs/roadmap.md) で管理します。

## 最新の公開ランタイムをインストール

```sh
ADOPTION_BASE="$(git rev-parse HEAD)"
STACK="${STACK:-generic}" # generic、python、go、rust、typescript、java、android、kotlin、flutter、swift、ruby、php、csharp
: "${AI_COCKPIT_TEMPLATE_PUBLIC_REPOSITORY:?このリリースの公開 Git remote を設定してください}"
: "${AI_COCKPIT_TEMPLATE_RAW_BASE:?対応する raw-content base を設定してください}"
PUBLIC_REPOSITORY="$AI_COCKPIT_TEMPLATE_PUBLIC_REPOSITORY"
RAW_BASE="$AI_COCKPIT_TEMPLATE_RAW_BASE"
RELEASE_TAG="$(curl -fsSL "${RAW_BASE}/main/release.json" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["releaseTag"])' 2>/dev/null || git ls-remote --tags --refs "$PUBLIC_REPOSITORY" 'v*' | python3 -c 'import re,sys; tags=[m.group(1) for line in sys.stdin for m in [re.search(r"refs/tags/(v\d+\.\d+\.\d+)$", line)] if m]; print(max(tags, key=lambda tag: tuple(map(int, tag[1:].split(".")))))')"
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL "${RAW_BASE}/${RELEASE_TAG}/install.sh" -o "$INSTALLER"
AI_COCKPIT_TEMPLATE_REPO="$PUBLIC_REPOSITORY" \
  AI_COCKPIT_TEMPLATE_REF="$RELEASE_TAG" sh "$INSTALLER" --stack "$STACK" --update-makefile --create-adoption
make ai-finish TASK=adopt_ai_cockpit
git add .
git commit -m "adopt AI Cockpit governance"
make check-ai-pr AI_BASE_COMMIT="$ADOPTION_BASE"
CONFIG_BASE="$(git rev-parse HEAD)"
make ai-start TASK=configure_ai_cockpit TITLE="Configure AI Cockpit for this project" MODE=code
```

導入先プロジェクトでは、ローカルの finish/archive 後に `git commit` を実行する前に人の許可を取り、さらに `git push` の前にも別の許可を取ります。PR の準備はツールで行えても、merge は人が手動で実行します。手動 merge 後、`make ai-close-work-item TASK=<task>` の実行にも明示的な許可を必要とし、自動 merge と自動 branch 削除は有効にしません。この保守的な gate は導入・upgrade の導入先プロジェクトにだけ適用し、template repository 自身の保守フローは変更しません。

このコマンドは公開済みの `release.json` を優先し、メタデータ移行中にファイルが存在しない場合は、公開済みのセマンティックバージョンタグから最新のものを選びます。その後、解決したタグのインストーラーのみをダウンロードして実行します。公開版の機能はソースツリーより遅れる場合があるため、初回導入 PR を作成する前に[インストール手順](docs/getting-started/installation.ja.md)を確認してください。
リリース元のメタデータやタグ付きインストーラーが公開されていない場合、このクイックインストールを匿名導入の前提として扱わないでください。`AI_COCKPIT_TEMPLATE_PUBLIC_REPOSITORY` と `AI_COCKPIT_TEMPLATE_RAW_BASE` はリリースタグの解決とインストーラーの取得にだけ使われ、インストーラー自体は `AI_COCKPIT_TEMPLATE_REPO` と `AI_COCKPIT_TEMPLATE_SOURCE` で clone / source の選択を行います。その場合はローカル clone か、明示的に設定した source を使ってください。

生成された設定用 Contract の変更範囲を確認・拡張してから、Project Profile、Guard、品質コマンド、CI を変更します。その後、ブロッキングゲートを有効にする前に実行系を対象プロジェクトへ適合させます。

<!-- governance-flow: install,configure-work-item,onboard,doctor,calibrate,confirm,validate,readiness,develop -->

```sh
make ai-onboard
# または個別に:
make cockpit-doctor
make cockpit-calibrate
# .ai/project_profile.proposed.yaml を確認し、承認済みの .ai/project_profile.yaml を作成する。
make check-ai-project-profile
make check-ai-guard-calibration
make check-ai-adoption-ready
make ai-finish TASK=configure_ai_cockpit
git add .
git commit -m "configure AI Cockpit for this project"
make check-ai-pr AI_BASE_COMMIT="$CONFIG_BASE"
```

この文書では、Project Profile を「プロジェクトプロファイル」、Guard を「ガード」、Scope を「変更範囲」、Summary を「変更サマリー」、Readiness Check を「導入準備チェック」として扱います。コマンド名や JSON フィールド名では英語の識別子を保持します。

プロジェクト診断（Doctor）はプロジェクトポリシーを変更せず、検出した事実、証拠、信頼度、提案、および不明点を記録します。境界校正（Calibration）は候補のみを生成し、ガード（Guard）の上書きや高リスクパスの承認は行いません。人が明示的に確認し、導入準備チェック（Readiness Check）が成功した後に、ガバナンス付きの AI タスクを開始します。

```sh
make ai-start TASK=example_change TITLE="Example change" MODE=code
```

チェックと監査記録付きで完了します。

```sh
make ai-finish TASK=example_change
```

## 仕組み

完全なガバナンス閉ループは **Intent → Contract → Implementation → Verification → Summary → Cockpit → Human Decision** です。以下の短いライフサイクルは、このアーキテクチャを操作する順序であり、閉ループそのものの置き換えではありません。

```text
Plan -> Scope -> Verify -> Summarize -> Status -> Archive
```

| 層 | 役割 |
| --- | --- |
| Work Item Contract | AI がファイルを変更する前にタスク境界を宣言する。 |
| Scope Guard | 宣言された変更範囲外の差分を検出し、完了・アーカイブ・マージのゲート通過を防ぐ。 |
| Backtrack Guard | 保護対象のテスト、スナップショット、Work Item 記録の削除を検出し、設定済みゲートの通過を防ぐ。 |
| Coverage Guard | 本番コードの各パスについて、プロジェクト所有の関連付けルールに一致するテストパスの変更を要求する。テスト内容の解析や実行時カバレッジの証明は行わない。 |
| Agent Risk Guard | プロンプト上の指示だけでは強制力を持たないリスク、作業途中の逸脱、不明点を残した完了申告に対する必須ゲート。 |
| AI Review Policy | ガバナンスや CI の変更について、レビュー時の注視点を Change Summary に明記するよう促す（報告のみ）。 |
| Checkpoint | 作業途中の整合性スナップショット。完了前に変更範囲の逸脱を検出する。 |
| Status Consistency Guard | `current_status.md` が現在作業中の Work Item と一致するか検証する。 |
| Change Summary | 変更内容、検証結果、残るリスクを記録する。 |
| Cockpit Status | 現在の AI タスク状態を生成ビューで表示し、Governance Compression の結果を反映する。 |
| Finish Flow | チェック通過後にのみ Work Item をアーカイブする。 |

## 信頼モデル

- `ai-start` は `baseCommit` と開始前から変更済みのパス、その内容のフィンガープリントを記録する。
- Contract v2 は `.ai/cockpit/checks.yaml` に登録された check ID のみ参照でき、任意コマンドを指定できない。
- `ai-finish` はチェック ID、終了コード、実行コミット、Contract ハッシュ、コマンドハッシュ、機密情報を除去した出力要約を記録する。これは構造化記録であり暗号学的証明ではない。
- インストーラーは同じ PR 検証スクリプトと Make ターゲットを配布する。Work Item のアーカイブ後、CI で `make check-ai-pr AI_BASE_COMMIT=<merge-base>` を実行する。
- 除外対象でない各 PR パスは、同じ Contract と Summary の組において、変更範囲と `changedFiles` の両方に含まれる必要がある。
- 制限対象・破壊的変更の承認は、Contract 内の自己申告型ワークフロー記録である。信頼できる人間の承認には CODEOWNERS、保護された CI 環境、またはプラットフォームの ID イベントを使用する。
- AI Cockpit は誤操作と作業途中の逸脱を抑える仕組みであり、悪意ある AI エージェントに対するセキュリティサンドボックスではない。上記で選択した公開版では、プロジェクトテストまたは `make ai-cockpit-quality` を独立した CI 必須チェックとして実行する。

## 何を検出するか

```text
[BLOCKED]
スコープ違反を検出しました。

許可されていないファイル変更：
- src/auth/payment.rs

許可されたスコープ：
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

<!-- stack-tiers: verified=python,go,rust,typescript,java,kotlin,ruby,php,csharp,flutter,android,swift; workflow-implemented=; preset-only=generic -->

- **ホステッド環境で検証済み:** `python`、`go`、`rust`、`typescript` は `real-stack-quality`、`java`、`kotlin`、`ruby`、`php`、`csharp` は `extended-real-stack-quality`、`flutter`、`android`、`swift` は `mobile-stack-quality` で最小プロジェクトの `make ai-cockpit-quality` を実行します。
- **Swift 検証範囲:** `mobile-stack-quality` は最小 Swift Package Manager fixture のみを対象とします。Xcode プロジェクト、workspace、CocoaPods はホステッド検証の対象外であり、導入後の Project Calibration が必要です。詳細は [インストール](docs/getting-started/installation.ja.md) と [Swift 適応例](examples/swift/README.md) を参照してください。
- **プリセットのみ:** `generic` は設定が完了するまで意図的に失敗します。
- **未対応の実行環境:** ネイティブ Windows シェル。WSL または別の POSIX 環境を使用してください。

スタックプリセットは、カスタマイズを前提とした出発点であり、依存ツールをインストールするものではありません。対象プロジェクトには、フォーマッター、テストランナー、SDK、ビルドプラグインがあらかじめ必要です。たとえば Java と Android は Gradle Wrapper と Spotless の設定、Python は Ruff と pytest を前提とします。`examples/` は一部のスタックのみを扱い、すべてのプリセットには対応していません。

ガバナンス実行系は対象言語に依存しませんが、スタックプリセットと既定のガード対象パスは、あらゆるフレームワークへの完全対応を意味しません。CI の必須チェックにする前に、対象リポジトリに合わせて `Makefile.ai.stack` と `.ai/guards/coverage_policy.yaml` を調整してください。

インストールで完了するのはガバナンス実行系の配置であり、本番運用向けの適合確認ではありません。Project Profile、Guard、品質コマンド、CI の適合は、別の `configure_ai_cockpit` Work Item が所有します。導入準備の検査には、承認済み Project Profile、Profile と Guard の整合性、実効性のある品質コマンド、確認済み Coverage 対象パス、および `ai-cockpit-quality` と `check-ai-pr` の CI 設定が必要です。この検査は静的な完全性確認であり、安全性やプロジェクトコマンドの妥当性を証明するものではありません。

<!-- release-capabilities: auditable-adoption,sha256-verification -->
<!-- public-quality-target: ai-cockpit-quality -->

現在の公開版には、監査可能な初回導入フローと、利用者が指定した SHA256 による検証機能が含まれています。リリース分配チェックは匿名で実行され、タグ元に公開アクセスできない場合は失敗として終了します。プロジェクト固有の品質コマンド、Coverage 対象パス、CI は引き続き明示的な調整が必要です。

## 動作環境要件

- Python 3.10 以上。
- merge-base および three-dot diff (`...`) をサポートする Git 環境。
- POSIX 準拠のシェルおよび GNU Make 実行環境。
- Linux および macOS は、ローカル実行および CI 用として公式にサポートされています。ネイティブの Windows シェルはサポートされていないため、WSL (Windows Subsystem for Linux) または他の POSIX ターミナルで実行してください。

リポジトリの `make quality` は、スクリプトカバレッジ全体の下限 80% とライフサイクル上重要な各スクリプトの回帰防止下限、`scripts/` と `tests/` への Ruff、すべてのガバナンススクリプトへの Mypy、中・高重要度を対象とする Bandit、Python コンパイル、差分検査、ドキュメント整合性検査を実行します。

## 詳細ドキュメント


- [インストール](docs/getting-started/installation.ja.md)
- [導入先プロジェクトの設定](docs/getting-started/adopter-configuration.ja.md)
- [最初の Work Item](docs/getting-started/first-work-item.ja.md)
- [概要・コンセプトガイド](docs/overview.ja.md)
- [ロードマップ (V1〜V4)](docs/roadmap.md)
- [フィールド解説書](docs/contract-fields.md)
- [Cockpit Status の読み方](docs/reference/how-to-read-cockpit-status.ja.md)
- [日本語リファレンス構成](docs/reference/documentation-architecture.ja.md)
- [設定](docs/configuration.ja.md)
- [アーキテクチャ](docs/architecture.ja.md)
- [トラブルシューティング](docs/reference/troubleshooting.ja.md)
- [設計思想](docs/design-philosophy.md)
- [ケーススタディ: AI rollback corruption](docs/case-study-ai-rollback-corruption.md)
- [各言語のサンプル](examples/)
既知リスク Guard は宣言された危険パターンを決定的に扱うもので、有限な回帰テストは未知の意味的リスクをすべて検出する証明ではありません。Work Item は、最新のリモート基盤 → 専用ブランチ → Contract/Preflight → 実装と検証 → Summary/アーカイブ → push → PR → merge → `make ai-close-work-item` → base 同期とブランチ清掃、という完全なライフサイクルを通過します。
