---
author: Ray
title: "Architecture"
description: AI Cockpit repository layout and component architecture.
keywords:
  - ai-cockpit
  - architecture
  - repository-layout
  - work-item-contract
---

# アーキテクチャ (Architecture)

## コンポーネントの依存関係とプロセスフロー

AI Cockpitフレームワーク内における、タスクの開始からPRの検証にいたるまでのライフサイクルとデータ/コントロールのフローは以下の通りです。

```mermaid
graph TD
    Start["ai-start (契約とサマリーの生成)"] --> Dev["開発/実装フェーズ"]
    Dev --> Check["check-ai (各種ガードによる検証)"]
    Check --> Finish["ai-finish (検証記録とステージ確認)"]
    Finish --> Archive["アーカイブ保存 (変更不可の履歴記録)"]
    Archive --> PR["check-ai-pr (PRレベルの統合監査)"]

    subgraph 状態とガバナンス
        Contract["Contract (契約書)"]
        Summary["Summary (成果サマリー)"]
        Guards["Guards (ポリシー監視)"]
        Status["Status (コックピット状態)"]
    end

    Start -->|生成| Contract
    Start -->|生成| Summary
    Dev -->|更新| Summary
    Check -->|ポリシーチェック| Guards
    Check -->|状態更新| Status
    Finish -->|検証完了| Summary
    Archive -->|読み取り専用として退避| Contract
    Archive -->|読み取り専用として退避| Summary
```


```text
.ai/
  cockpit/
    README.md
    checks.yaml
    current_status.md
  guards/
    agent_risk_policy.yaml
    ai_review_policy.yaml
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
.cursor/
  rules/
    ai-cockpit.mdc
examples/
  csharp/
  flutter/
  go/
  java/
  kotlin/
  php/
  python/
  ruby/
  rust/
  swift/
  typescript/
docs/
  assets/
    ai-cockpit-demo.gif
scripts/
  ai_archive_work_item.py
  ai_check_agent_risk.py
  ai_check_backtrack.py
  ai_check_coverage_guard.py
  ai_check_guards.py
  ai_check_review_policy.py
  ai_check_scope.py
  ai_check_status.py
  ai_check_status_consistency.py
  ai_check_summary.py
  ai_check_work_item.py
  ai_checkpoint.py
  ai_common.py
  ai_finish.py
  ai_generate_status.py
  ai_observability.py
  ai_start.py
  install_ai_cockpit.py
target/
  ai_observability.jsonl
  ai_*.json
templates/
  make/
    Makefile.ai
  stacks/
    *.mk
install.sh
Makefile
AGENTS.md
CLAUDE.md
GEMINI.md
```

## コアコンポーネント (Core Components)

| コンポーネント | 目的・役割 |
| --- | --- |
| Work Item Contract | タスクのスコープ、参照ソース、受け入れ基準、検証項目、およびロールバック手順を宣言します。 |
| Scope Guard | 実際の Git 差分が `scope` 内に収まり、`outOfScope` に抵触していないかをチェックします。 |
| Backtrack Guard | デフォルトで、保護されたテスト、スナップショット、またはワークアイテム証跡の削除をブロックします。 |
| Coverage Guard | デフォルトで、対応するテストコードの変更を伴わないプロダクションコードの変更をブロックします。 |
| Agent Risk Guard | プロンプトインジェクション対策、開発途中のタスクのブレ、および不明点の積み残しに対する厳格なチェックゲートです。 |
| AI Review Policy | ガバナンスや CI 関連ファイルの変更など、レビュー時に特に注視すべき変更をフラグ立てするレポート機能です。 |
| Checkpoint | 開発中の整合性スナップショットであり、スコープ、受け入れ、および検証状態のドリフトを検出します。 |
| Status Consistency Guard | `current_status.md` が現在のアクティブなワークアイテムと一致しているかを検証します。 |
| Change Summary | 変更されたファイル、合格した検証、リスク評価、生成ファイル、および破壊的変更の履歴を記録します。 |
| Cockpit Status | アクティブな AI タスクの現在の状態を統合表示するステータス画面を生成します。 |
| Observability | 各チェックの実行ごとに構造化された JSONL イベントを `target/ai_observability.jsonl` に追記します。 |
| Finish Flow | 必須の検証チェックを実行し、合格した場合にワークアイテムをアーカイブします。 |

## 差分と検証証跡のセマンティクス (Diff and Evidence Semantics)

ワークアイテムの基準点（ベースライン）は、タスク開始時に取得される Git コミットです。有効な変更セットは、`baseCommit...HEAD` 間の差分、`HEAD` に対するステージング/未ステージングの変更、および未追跡ファイル（untracked files）の論理和として定義されます。開始時点で dirty であったパスは、そのファイルのハッシュ値（fingerprint）が変化しない限り、スコープチェック対象から除外されます。CI 環境においては、`AI_BASE_COMMIT` 環境変数を設定することで、プルリクエストのマージベース（merge-base）をベースラインとして上書きできます。

検証の実行は、Contract に直接記述された自由なコマンド文字列ではなく、レジストリ（`.ai/cockpit/checks.yaml`）によって管理されます。v2 形式の Contract ではチェック ID を指定し、それぞれのチェック ID は対応する Makefile の明示的なターゲット名へと解決されます。Finish フローの実行時、チェック ID、実行コミット、Contract のハッシュ、および正規化されたコマンドハッシュが検証メタデータとして記録されます。これにより、検証後の契約の改ざんや偽造を検知できますが、暗号的な証明（Cryptographic Attestation）を構成するものではありません。

PR 監査（`check-ai-pr`）では、プルリクエストに含まれるすべてのアーカイブされた Contract および Summary、あるいはレビュー記録が走査されます。新しい検証証跡は、Contract と Summary がペアで同時に追加される必要があります。既存のアーカイブされた証跡は不変（Immutable）であり、過去の変更履歴の修正、削除、名前変更は拒否されます。これにより、後発のタスクが過去の検証証跡を流用することを防ぎます。また、監査対象となるすべての変更パスは、いずれかのアクティブ/アーカイブ済みワークアイテムの `scope` 内に含まれ、且つ `changedFiles` に記録されている必要があります（この PR 監査の段階では、開始時の dirty ファイル除外ロジックは無効化されます）。

PR のアーカイブ検証には必ず Contract v2 形式を使用する必要があります。v1 形式はローカルの歴史的調査のためにのみ読み込み可能として許容されますが、PR で新規追加または変更された場合は、検証レジストリや実行メタデータの迂回を防ぐために拒否されます。

リポジトリ内の承認フィールド（`approvedBy` 等）は、ワークフロー上の意思决定プロセスを記録するものであり、厳密な人間の個人認証を提供するものではありません。AI Cockpit は AI エージェントの自律的な安全ガードを目的とした変更管理ワークフローであり、悪意のあるエージェントを隔離するセキュリティサンドボックスではありません。信頼された人間による最終承認や独立したビルドテストの実行は、コードホスティングプラットフォームの保護されたブランチ設定や保護された CI 環境で実施される必要があります。
