---
author: Ray
title: "AI Cockpit 概要ガイド"
description: AI Cockpit の設計思想、制御アーキテクチャ、およびライフサイクルの全体像
---

# AI Cockpit 概要ガイド

AI Cockpit は、AI コーディングエージェント（Gemini、Claude、Codex、Cursor など）によるソースコードの変更範囲を定義し、検証結果と履歴を記録するための**変更管理ガバナンスフレームワーク**です。

---

## 1. コアコンセプト：5 つのライフサイクル層

AI Cockpit は、変更管理の流れを以下の 5 つのライフサイクル層として整理します。個別の Guard や Policy の数を 5 つに限定するモデルではありません。

```
[ 計画 ] ──> [ 境界 ] ──> [ 検証 ] ──> [ 記録 ] ──> [ 状態 ]
 Contract      Guards      Checks      Summary      Status
```

1. **計画（Work Item Contract）**:
   - AI エージェントが変更を行う前に、物理的なスコープ (`scope`)、除外対象 (`outOfScope`)、受け入れ基準 (`acceptance`)、必要な検証 (`verification`) を事前宣言する「契約書」。
2. **境界（Scope & Guard Policies）**:
   - 変更されたファイル（Git 差分）が Contract のスコープ内に収まっているかを検出する Scope Guard。書き込み自体を事前に禁止する機能ではありません。
   - テストやドキュメントなどの勝手な削除を検知する Backtrack Guard。
   - 本番コードを変更する場合に、対応するテスト変更を要求する Coverage Guard。
3. **検証（Verification Registry）**:
   - コマンドを直接 Contract に記述することを禁止し、登録済みの Make ターゲット（`checks.yaml` に定義）のみに限定することで、任意命令が混入するリスクを低減。
4. **記録（AI Change Summary）**:
   - 実際にどのファイルをどのような理由で変更したか、どのような検証を行い、どのような残留リスクが存在するかを監査証跡として保存。
5. **状態（Cockpit Status）**:
   - プロジェクトの AI ガバナンス状況を `current_status.md` という単一のステータスファイルに統合表示し、レビュアーの認知的負荷を軽減。

アーカイブは、状態検証後に Contract と AI Change Summary を PR 監査証跡として移動するライフサイクルの完了処理です。独立した第6層ではありません。

具体的な制御は各層に複数存在し、動作も異なります。

| 種別 | 主な制御 | 動作 |
|---|---|---|
| ブロッキング | Contract、Scope Guard、Agent Risk Guard、Backtrack Guard、Coverage Guard、Status Consistency、Adoption Readiness、PR Aggregate Ownership | 条件を満たさない場合、完了・アーカイブ・マージ用チェックを失敗させる |
| 報告型 | AI Review Policy | ガバナンス変更のレビュー注視点を報告し、Summary への記録を促す |

---

## 2. ワークフロー・ライフサイクル

AI Cockpit の管理プロセスは、以下のライフサイクルに従って進行します。

1. **タスク開始（`make ai-start`）**:
   - `TASK`、`TITLE`、`MODE` を指定し、Work Item Contract と AI Change Summary のスケルトンを生成します。
   - 開始時に、既存のローカル変更を内容ハッシュ（fingerprint）付きで記録し、開始後の差分と区別します。
2. **用語集の確認 (`.ai/glossary.md`)**:
   - エージェントは設計の初期段階で必ずプロジェクト固有の用語集を読み込み、ドメイン概念の誤解や命名のブレを防ぎます。
3. **コード変更と自己検証（Development & Verify）**:
   - Contract で定義された `scope` の範囲内のみを変更し、`acceptance` の受け入れ基準を自己検証します。
4. **タスク完了（`make ai-finish`）**:
   - `aiGuidelines` を含むすべての検証ゲートがパスし、AI Change Summary と Cockpit Status が一致した段階で、Work Item を `.ai/work-items/archive/` に移動します。

---

## 3. 品質と安全性のためのルール

- **ゼロ外部依存の堅牢性**:
  - 本フレームワークのスクリプトは、依存パッケージのインストールが不可能な CI 環境や開発環境でも動作するよう、Python 標準ライブラリのみで構成されています。
  - 内蔵の YAML パーサは、インデントの乱れや文法エラーを検知するとサイレントに無視せず、明示的にエラー (`ValueError`) を発生させてガバナンスの崩壊を防ぎます。
- **デバッグ情報の可視化 (Explainability)**:
  - ガードが差分を走査する際、どのファイルがどのパターンによって許可/ブロックされたかの詳細なマッチング理由を出力し、監査観点からのデバッグや調査を容易にします。
