---
author: Ray
title: "Contract and Summary Fields"
description: Work Item Contract v2 と AI Change Summary のフィールドリファレンス。
---

# AI Cockpit フィールド・スキーマ解説書

本ドキュメントでは、AI Cockpit 変更管理フレームワークにおける **Work Item Contract (契約)** および **Change Summary (要約)** 内の各フィールドについて、スキーマ定義と期待される値を解説します。

---

## 1. Work Item Contract (`*.contract.json`)

AI エージェントがコード開発を開始する前に、タスクの境界と検証要件を定義するファイルです。

### 1.1 基本メタデータ

- **`contractVersion`**: `int` (必須)
  - 契約スキーマのバージョン。チェック ID に基づく厳格な v2 契約の検証を強制するため、現在は `2` を指定します（v1 形式はレガシーアーカイブでのみ読込互換として許容され、新規開発での記述は拒否されます）。
- **`workItemId`**: `string` (必須)
  - 本タスクのユニークな識別子。小文字の英数字とアンダースコア（`a-z0-9_`）で記述します。ファイル名（`<workItemId>.contract.json`）と一致させる必要があります。
- **`mode`**: `string` (必須)
  - 開発フェーズ。`investigate`（調査中）、`author_todo`（実装前 TODO の作成）、`code`（実装中）、`review`（レビュー中）、`cleanup`（片付け・クリーンアップ）のいずれかを指定します。
- **`title`**: `string` (必須)
  - タスクの簡潔なタイトル。
- **`baseCommit`**: `string` (必須)
  - タスクを開始する基準となった、有効な Git コミットのオブジェクト ID。ハッシュ方式や文字数を SHA-1 に限定しません。

`baseCommit` is the immutable migration boundary for Work Item behavior. New
schema or archive rules must use the recorded commit or explicit schema fields,
never a mutable archive-count threshold. `archiveSequence` is ordering
metadata; strict archive integrity is enabled by the row's own digest pair.

### 1.2 変更追跡と範囲

- **`baselineDirtyPaths`**: `array[object]`
  - タスク開始時にすでに編集されていた未コミットファイル（dirty files）のリスト。
  - 各要素のオブジェクト構造:
    - `path`: `string` - リポジトリ相対のファイルパス。
    - `status`: `string` - Git ステータス（`M` など）。
    - `fingerprint`: `string` - 開始時点のファイルハッシュ。これによって開始前からの差分と本タスク内の差分を識別し、不要な範囲外チェック違反を防ぎます。
- **`adoptionBootstrapPaths`**: `array[string]` (初回導入専用)
  - `workItemId: adopt_ai_cockpit` のインストーラー生成 Contract だけが使用できます。指定パスは通常の scope と PR の完全差分所有権検証を受けますが、初回導入時に限り、ガバナンススクリプト変更にテスト差分を求める companion rule の対象外になります。一般タスクのテスト要件を回避するためには使用できません。
- **`scope`**: `array[string]` (必須)
  - AI エージェントに許可するリポジトリ相対のパスまたは Glob パターン。適合しない差分は `Scope Guard` がチェック時に検出し、完了・アーカイブ・マージのゲート通過を防ぎます。ファイルシステムへの書き込み自体を事前に禁止する機能ではありません。
- **`outOfScope`**: `array[string]`
  - AI エージェントが編集してはならないパスまたは Glob パターン。
- **`sources`**: `array[object]`
  - 設計や意思決定の根拠としたソース情報。
  - `path`: `string` - 設計ドキュメントやチケットへのパス。
  - `reason`: `string` - 参照した理由。
- **`problemStatement`**: `string` (任意)
  - この Work Item が解決するユーザー向けまたはエンジニアリング上の問題を簡潔に記述します。一行の要約として機能します。
  - 製品コンテキストが与えられていない場合は、推測せずにその旨を明記します。
  - 既存ワークフローとの後方互換性を保つため、必須にはしませんが、指定した場合は空文字列にできません。
- **`intent`**: `object` (任意、V2 以降)
  - AI が「なぜこの変更が存在するか」を理解するための詳細な意図を記述します。
  - `intent` セクション全体を省略することも、一部のフィールドのみ記述することも許容されます。
  - `problemStatement` との関係: `problemStatement` は一行の要約として残し、`intent.problem` にはより詳細な背景・現状・差距を記述します。両フィールドは共存可能であり、現時点で `problemStatement` を廃止する予定はありません。
  - フィールド一覧（全て任意）:
    - `businessGoal`: `string` — ビジネス上の目的。
    - `userGoal`: `string` — ユーザー視点の目的。
    - `problem`: `string` — 解決すべき課題の詳細な背景・現状・差距の説明。
    - `constraints`: `array[string]` — 実装上または設計上で守るべき制約。
    - `nonGoals`: `array[string]` — 今回のスコープで意図的に解決しないこと。
    - `rationale`: `string` — このアプローチを選択した理由。
  - 現時点で最も記入されやすいフィールドは `problem`、`constraints`、`rationale` です。将来の AI ワークフローが成熟するにつれて残りのフィールドが徐々に活用されることを想定しています。


### 1.3 意思決定と安全性

- **`unknowns`**: `array[string]`
  - 実装前に解決すべき不明点・設計未決事項のリスト。
  - **重要**: `mode` が `code` (実装中) の場合、`unknowns` は空（`[]`）でなければならず、未決事項を残したままの実装フェーズ進行はエージェントリスクチェックによって拒否されます。
- **`notCodable`**: `boolean`
  - 設計矛盾や不明点が多すぎてコード変更に着手できない場合に `true` に設定します。
  - **重要**: `mode: code` の場合は必ず `false` でなければなりません。
  - Preflight では `true` が直接 `not_ready` を導きます。エージェントは実装を停止し、Contract を更新するまで再開してはいけません。
- **`riskAssessment`**: `object`
  - **`level`**: `"low" | "medium" | "high"`
  - **`riskTypes`**: 該当するリスク分類（例: `scope_unclear`, `api_change`）。
  - **`reason`**: リスク判定の根拠。
- **`agentCapability`**: `object`
  - AI エージェント自身による実装・検証能力の自己申告。
  - `canImplement`: `boolean` (コード変更能力の有無)
  - `canVerify`: `boolean` (自身で検証を走らせる能力の有無)
  - `needsHumanDecision`: `boolean` (人間の介入や追加意思決定が必要か)
  - `blockedReason`: `string` (ブロックされている場合の原因)
  - Preflight では、宣言済みの `canImplement: false`、`canVerify: false`、または `needsHumanDecision: true` が `not_ready` を導き、ユーザーへの報告と pause が必要です。
- **`executionDecision`**: `object`
  - 開発続行の決定。
  - `status`: `"continue" | "defer" | "needs_human_decision" | "block"`
  - `reason`: その意思決定の理由。
  - Preflight では `block`、`defer`、`needs_human_decision` が `not_ready` を導きます。`continue` 以外で実装を続けることはできません。
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
    - `required`: `boolean` - `true` の場合、失敗すると Finish を実行できません。

---

## 2. Change Summary (`*.summary.json`)

開発完了時に AI エージェントが変更結果とエビデンス（検証の証拠）を記録するファイルです。

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
    - `runner`: 検証を実行したプログラム。形式の一貫性を保つため `ai_finish` のみ許可されますが、信頼できる実行者の身元証明ではありません。
    - `executedAt`: ISO-8601 形式のタイムスタンプ。
    - `exitCode`: コマンド終了コード（`0` はパス）。
    - `durationMs`: 実行にかかったミリ秒。
    - `outputDigest`: コマンド標準出力の SHA-256 ハッシュ値。
    - `commandHash`: コマンド文字列の SHA-256 ハッシュ値（コマンドの勝手な差し替えを検知）。
    - `contractHash`: 実行時の Contract ファイルのハッシュ値。Summary と現在の Contract の不一致検出に使用しますが、暗号学的な耐改ざん証明ではありません。
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
  - 各要素のスキーマ:
    - `level`: `"low" | "medium" | "high"`
    - `area`: 該当するシステム領域。
    - `detail`: リスクの詳細説明。
    - `reviewRecommended`: `boolean` - レビューで特に注視すべきか。
    - `followUpCandidate`: `boolean` - 別タスクを起票して後続対応すべきか。
- **`reviewReadiness`**: `object`
  - レビューの準備状況。
  - `status`: `"ready" | "ready_with_risks" | "not_ready" | "blocked"`
  - `reason`: その状態である理由。
  - `expectedReviewFocus`: レビュー時に特に注視してほしい具体的な観点の配列。
- **`scenarioCoverage`**: `array[object]` (任意、V2.6 以降)
  - 中高リスク Work Item で、どのリスクドメインのシナリオが verified / unverified / not_applicable なのかを示す通用的な証跡です。
  - 各オブジェクトの構造:
    - `scenario`: `string` - シナリオ名。必須で、空文字列は不可です。
    - `required`: `boolean` - そのシナリオが必須かどうか。
    - `status`: `"verified" | "unverified" | "not_applicable"`
    - `evidence`: `array[string]` - 検証証跡。`verified` の場合は空にできません。
    - `reason`: `string` - `not_applicable` の場合は必須、`unverified` の場合は推奨です。
  - シナリオ内容は Core の既定ライブラリではなく Work Item 側が保持し、Core は構造と状態だけを検証します。
  - `.ai/guards/scenario_coverage_policy.yaml` は、どの `hardRiskTypes` に scenario coverage を要求するかを決める共通ポリシーです。シナリオ名や証跡の内容は Work Item 側に残します。
- **`followUps`**: `array[string]` (Summary)
  - 現在の Work Item では解決しないが、後続タスクとして追跡すべき項目の一覧です。
- **`unverifiedScenarios`**: `array[string]` (Summary)
  - 未検証のまま残っているシナリオ名の一覧です。`unknowns` や `residualRisks` とは別に扱います。
- **`knownGaps`**: `array[string]` (Summary)
  - 本タスクで意図的に未対応にした、または積み残した要件です。`residualRisks` は残存リスク、`knownGaps` は意図的な未対応項目として分けて扱います。
- **`intentAlignment`**: `object` (任意、V2 以降)
  - Summary における Intent 達成度の要約です。`intentAlignment` 全体を省略することも、`null` にすることも、空オブジェクトや部分的な記入にすることも許容されます。
  - フィールド一覧（全て任意）:
    - `problemResolved`: `boolean` — 意図した問題が解決されたか。
    - `constraintsRespected`: `boolean` — Contract に書かれた制約が守られたか。
    - `nonGoalsAvoided`: `boolean` — 今回の非目標を増やさずに済んだか。
    - `rationaleValidated`: `string` — このアプローチが妥当だった理由の要約。
  - `intentAlignment` は Intent に対する完了時の確認であり、Summary の他の証跡を置き換えません。Context がない場合は空のままにできます。

### 2.5 Cockpit Compression との関係

V2.5 の Cockpit は Summary をそのまま複製せず、`reviewReadiness`、`residualRisks`、`verification`、`guidelinesCompliance`、`checkpointEvidence`、`intentAlignment` を圧縮して Human Decision State を生成します。V2.6 では `scenarioCoverage`、`followUps`、`unverifiedScenarios` が追加されます。

- `reviewReadiness` は recommendation の直接入力です。
- `residualRisks` は `ready_with_risks` と `needs_investigation` の判断材料になります。
- `verification` は `blocked` / `needs_investigation` / `ready_for_review` の主要ドライバです。
- `scenarioCoverage` は `complete` / `incomplete` / `not_required` / `unknown` の信号に圧縮されます。
- `followUps` と `unverifiedScenarios` は、`unknowns` や `residualRisks` と混用せず、未検証シナリオを明示するために使います。
- `intentAlignment` は V2 の Intent に対する整合性の補助証拠です。
- `checkpointEvidence` は長期タスクの整合性と evidence freshness を維持します。
- `.ai/guards/scenario_coverage_policy.yaml` により、どの `hardRiskTypes` に `scenarioCoverage` が必要かが決まります。ポリシー自体は機構であり、シナリオ内容は Work Item の責任です。

Cockpit の出力は Summary の代替ではなく、Summary から派生した人間向けの圧縮表示です。詳細な定義は [Cockpit Status の読み方](reference/how-to-read-cockpit-status.md) を参照してください。

---

## 3. 追加の監査フィールド

Summary では、レビュー経緯やユーザーからの修正を追跡するために、以下のメタデータも記録できます。

- **`checkpointReview`**: `array[object]` (Summary)
  - 人間や AI 自体による中途チェックポイントでのレビュー結果、及び判定理由を保存する配列。
- **`userCorrectionsCaptured`**: `array[object]` (Summary)
  - 開発中、人間の開発者が AI エージェントの誤った方針やバグを直接指摘して修正させた履歴のログ。
- **`userCorrectionSolidification`**: `array[object]` (Summary)
  - 捕獲された上記の「人間の修正指示」を、今後二度と同じエラーを起こさないよう、どのように共通の `guards/*.yaml` ポリシーや `glossary.md` にルールとして昇華したかの記録。
