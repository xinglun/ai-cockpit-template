---
author: Ray
---

# AI Cockpit フィールド・スキーマ解説書

本ドキュメントでは、AI Cockpit 変更管理フレームワークにおける **Work Item Contract (契約)** および **Change Summary (要約)** 内の各フィールドについて、スキーマ定義、期待される値、および Sentinel などの本番運用で活用されている拡張フィールドも含めて詳細に解説します。

---

## 1. Work Item Contract (`*.contract.json`)

AI 代理（AI Agent）がコード開発を開始する前に、タスクの境界と検証要件を定義するファイルです。

### 1.1 基本メタデータ

- **`contractVersion`**: `int` (必須)
  - 契約スキーマのバージョン。チェック ID に基づく厳格な v2 契約の検証を強制するため、現在は `2` を指定します（v1 形式はレガシーアーカイブでのみ読込互換として許容され、新規開発での記述は拒否されます）。
- **`workItemId`**: `string` (必須)
  - 本タスクのユニークな識別子。小文字の英数字とアンダースコア（`a-z0-9_`）で記述します。ファイル名（`<workItemId>.contract.json`）と一致させる必要があります。
- **`mode`**: `string` (必須)
  - 開発フェーズ。`investigate` (調査中)、`code` (実装中)、`review` (レビュー中)、`cleanup` (片付け・クリーンアップ) のいずれかを指定します。
- **`title`**: `string` (必須)
  - タスクの簡潔なタイトル。
- **`baseCommit`**: `string` (必須)
  - タスクを開始する基準となった Git コミットの 40 桁の SHA-1 ハッシュ値。

### 1.2 変更追跡と範囲

- **`baselineDirtyPaths`**: `array[object]`
  - タスク開始時にすでに編集されていた未コミットファイル（dirty files）のリスト。
  - 各要素のオブジェクト構造:
    - `path`: `string` - リポジトリ相対のファイルパス。
    - `status`: `string` - Git ステータス（`M` など）。
    - `fingerprint`: `string` - 開始時点のファイルハッシュ。これによって開始前からの差分と本タスク内の差分を識別し、不要な範囲外チェック違反を防ぎます。
- **`scope`**: `array[string]` (必須)
  - AI 代理が変更を許可されるリポジトリ相対のパスまたは Glob パターン。これに適合しないファイル編集は `Scope Guard` によって遮断されます。
- **`outOfScope`**: `array[string]`
  - AI 代理が絶対に編集してはならないパスまたは Glob パターン。
- **`sources`**: `array[object]`
  - 設計や意思決定の根拠としたソース情報。
  - `path`: `string` - 設計ドキュメントやチケットへのパス。
  - `reason`: `string` - 参照した理由。

### 1.3 意思決定と安全性

- **`unknowns`**: `array[string]`
  - 実装前に解決すべき不明点・設計未決事項のリスト。
  - **重要**: `mode` が `code` (実装中) の場合、`unknowns` は空（`[]`）でなければならず、未決事項を残したままの実装フェーズ進行はエージェントリスクチェックによって拒否されます。
- **`notCodable`**: `boolean`
  - 設計矛盾や不明点が多すぎてコード変更に着手できない場合に `true` に設定します。
  - **重要**: `mode: code` の場合は必ず `false` でなければなりません。
- **`riskAssessment`**: `object`
  - **`level`**: `"low" | "medium" | "high"`
  - **`riskTypes`**: 該当するリスク分類（例: `scope_unclear`, `api_change`）。
  - **`reason`**: リスク判定の根拠。
- **`agentCapability`**: `object`
  - AI 代理自身の実装・検証能力自己申告。
  - `canImplement`: `boolean` (コード変更能力の有無)
  - `canVerify`: `boolean` (自身で検証を走らせる能力の有無)
  - `needsHumanDecision`: `boolean` (人間の介入や追加意思決定が必要か)
  - `blockedReason`: `string` (ブロックされている場合の原因)
- **`executionDecision`**: `object`
  - 開発続行の決定。
  - `status`: `"continue" | "defer" | "needs_human_decision" | "block"`
  - `reason`: その意思決定の理由。
- **`destructiveChangePolicy`**: `object`
  - 破壊的変更（ファイルの削除、テストやスナップショットの整理など）のポリシー。
  - `allowed`: `boolean`
  - `requiresHumanApproval`: `boolean`
  - `allowPatterns`: 削除が許可される Glob パターン。
- **`restrictedWriteApproval`**: `object`
  - CI 設定や Makefile などの高セキュリティ制限ファイルへの書き込み承認記録。
  - `approved`: `boolean`
  - `approvedBy`: `"Ray"` などの承認者名。
  - `reason`: 承認の背景。
- **`rollbackNote`**: `string`
  - 万が一変更を元に戻す（ロールバック）ことになった場合の具体的な手順や注意書き。

### 1.4 受入基準と検証項目

- **`acceptance`**: `array[string]`
  - 本タスクの人間が期待する受入要件（TODOリスト）。
- **`guidelines`**: `array[string]`
  - 本タスクに適用される追加の開発・品質ガイドライン（例:「新規 API には doc コメントを必須とする」など）。
- **`verification`**: `array[object]`
  - `make ai-finish` で検証が強制されるチェックのリスト。
  - 各要素の構造:
    - `check`: `string` - `aiScope` や `aiAgentRisk` などの `.ai/cockpit/checks.yaml` に登録されたチェック名。
    - `required`: `boolean` - `true` の場合、成否が阻断（Finish 不可）に直結します。

---

## 2. Change Summary (`*.summary.json`)

開発完了時に AI 代理が変更結果とエビデンス（検証の証拠）を記録するファイルです。

### 2.1 変更実績と成果

- **`workItemId`**: `string` (必須)
  - 対応する Contract の `workItemId` と完全に一致する必要があります。
- **`contractPath`**: `string` (必須)
  - この Summary が対応している Contract ファイルへのリポジトリ相対パス。
- **`changedFiles`**: `array[object]`
  - 実際に変更・新規作成したファイルのリスト。
  - `path`: `string` - ファイルパス。
  - `reason`: `string` - なぜその変更が必要だったかの簡潔な理由。
- **`sourcesUsed`**: `array[string]`
  - 実際に開発中に利用したソース資料や成果物。
- **`generatedFiles`**: `array[string]`
  - 本タスクによって自動生成されたファイルのパス。
- **`destructiveChanges`**: `array[object]`
  - 実際に実行された破壊的変更（ファイルの削除など）の記録と理由。

### 2.2 検証エビデンスとガイドライン準拠

- **`verification`**: `array[object]`
  - `make ai-finish` 実行時に自動生成される各検証チェックのエビデンス情報。
  - 各オブジェクトには以下が含まれます:
    - `check`: チェック名。
    - `result`: `"passed" | "failed" | "not_run"`
    - `runner`: 検証を実行したプログラム。手動偽造を防ぐため `ai_finish` のみ許可されます。
    - `executedAt`: ISO-8601 形式のタイムスタンプ。
    - `exitCode`: コマンド終了コード（`0` はパス）。
    - `durationMs`: 実行にかかったミリ秒。
    - `outputDigest`: コマンド標準出力の SHA-256 ハッシュ値。
    - `commandHash`: コマンド文字列 of SHA-256 ハッシュ値（コマンドの勝手な差し替えを検知）。
    - `contractHash`: 実行時の Contract ファイルのハッシュ値（検証後の Contract 改ざんを検知）。
    - `commitSha`: 実行時点の Git コミット SHA。
    - `outputSummary`: 機密情報（API キーなど）や絶対パスがマスク (`[REDACTED]`) された、出力の先頭約 500 文字。
- **`guidelinesCompliance`**: `array[object]`
  - Contract で指示された各ガイドラインに対する準拠証拠。
  - `guideline`: `string` - ガイドライン文章。
  - `compliant`: `boolean` - 準拠しているか。
  - `evidence`: `string` - 具体的な準拠の証明（例: 「仕様書ドキュメントに JSDoc を追記した」）。

### 2.3 チェックポイント監査証跡

- **`checkpointEvidence`**: `array[object]`
  - 開発工程のチェックポイント（`before_edit` / `before_finish` など）におけるスナップショット。
  - スキーマ構造:
    - `stage`: `"before_edit" | "before_finish"` など。
    - `recorded`: `boolean`
    - `detail`: 記録時のメモ。
    - `contractHash`: 記録時点の Contract ハッシュ（新鮮度チェック用）。
    - `acceptanceCount`, `unknownCount`, `requiredChecks`, `requiredChecksPassed`: 記録時点の各種カウンタの `int` 値。これが最新の契約とズレていると、エージェントリスクチェックによって開発が一時中断されます。

### 2.4 リスクとレビュー準備度

- **`risk`**: `object`
  - 完成時点のリスク再評価。`level` と `detail` を含みます。
- **`observedIssues`**: `array[string]`
  - 開発中に見つかった副作用やコードベースの問題、リファクタリング推奨事項など。
- **`residualRisks`**: `array[object]`
  - 人間のレビュー担当者に引き継ぐべき残存リスク。
  - **Sentinel 拡張スキーマ**:
    - `level`: `"low" | "medium" | "high"`
    - `area`: 該当するシステム領域。
    - `detail`: リスクの詳細説明。
    - `reviewRecommended`: `boolean` - レビューで特に注視すべきか。
    - `followUpCandidate`: `boolean` - 別タスクを起票して後続対応すべきか。
- **`reviewReadiness`**: `object`
  - レビューの準備状況。
  - `status`: `"ready" | "not_ready"` (Sentinel では `"ready_with_risks"` を許容)
  - `reason`: その状態である理由。
  - `expectedReviewFocus`: レビュー時に特に注視してほしい具体的な観点の配列。
- **`knownGaps`**: `array[string]`
  - 本タスクで意図的に未対応にした、または積み残した要件。

---

## 3. Sentinel 固有の高度な拡張フィールド

Sentinel などの成熟した商用プロダクトでは、ガバナンスをさらに強固にするために、テンプレートの Summary に以下のメタデータ構造を追加して記録しています。

- **`checkpointReview`**: `array[object]` (Summary)
  - 人間や AI 自体による中途チェックポイントでのレビュー結果、及び判定理由を保存する配列。
- **`userCorrectionsCaptured`**: `array[object]` (Summary)
  - 開発中、人間の開発者が AI 代理の誤った方針やバグを直接指摘して修正させた（軌道修正）履歴のログ。
- **`userCorrectionSolidification`**: `array[object]` (Summary)
  - 捕獲された上記の「人間の修正指示」を、今後二度と同じエラーを起こさないよう、どのように共通の `guards/*.yaml` ポリシーや `glossary.md` にルールとして昇華したかの記録。
