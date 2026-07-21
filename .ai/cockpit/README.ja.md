---
author: Ray
title: "AI Cockpit"
description: AI Cockpit ワークスペース概要とワークフローガイド（日本語）。
keywords:
  - ai-cockpit
  - work-item-contract
  - scope-guard
  - change-summary
  - cockpit-status
---

# AI Cockpit

[English](README.md)

AI Cockpit は、エージェント型開発のための協調エンジニアリング環境です。Codex、Gemini、Claude、Cursor、Antigravity などのコーディングエージェントに、ファイル変更前の共通運用契約を提供します。

コックピットは言語非依存です。明示的なスコープ、委譲されたチェック、レビュー証跡、監査可能なタスク記録を通じて AI Change Governance を提供し、Makefile はプロジェクト固有のチェックを各リポジトリでカスタマイズ可能なコマンドへ委譲します。

## コアファイル

- `checks.yaml`: チェックカタログとプロジェクト固有コマンドの選択指針。
- `current_status.md`: アクティブ Work Item の生成済みステータスビュー。
- `.ai/work-items/active/*.contract.json`: 作業開始前のタスク境界。
- `.ai/work-items/active/*.summary.json`: 完了前の変更レポート。
- `.ai/guards/*.yaml`: ファイル所有権、境界、スコープ、バックトラック、カバレッジルール。

## フロー

### リポジトリの役割とレビュー単位
既定のレビュー単位は「1 Work Item、1 専用作業ブランチ、1 Pull/Merge Request」です。無関係な Work Item を同じブランチや PR に混在させないでください。
ブランチの起点はリポジトリの役割で決まります。

- テンプレートリポジトリでは、最新の `origin/main` から保守ブランチを作成する。
- 導入先プロジェクトでは、そのプロジェクト自身のリモート既定ブランチの最新コミットから作成する。`origin/main` を仮定せず、リモート名とブランチ名を確認し、Work Item に `baseRemote`、`baseBranch`、`baseCommit` を記録する。
インストールとアップグレードの変更履歴は導入先プロジェクト側に属します。移動するテンプレート作業ブランチではなく、公開済みテンプレートのリリースタグを使用してください。PR のマージ後は、明示的な復旧例外を除き、リモートとローカルの作業ブランチを削除します。

### ライフサイクルのクローズ

Work Item を archive し、対応する PR が merge された後に `make ai-close-work-item TASK=<task>` を実行します。Contract/Summary/Cockpit Status、ブランチと PR の一対一対応、fast-forward のみの base 同期、ローカル／リモートブランチ削除、clean な repository、local base と remote base の一致を検証します。どれかが失敗した場合は fail closed とし、全ての事後条件を満たすまで `ready for next Work Item` を報告しません。

`ai-close-work-item` は worktree を考慮します。base branch が別の worktree で checkout 済みの場合、その worktree が clean であることを確認し、そこで base を fast-forward と検証した後、Work Item worktree を detached にして local／remote の Work Item branch を削除します。過去の archive 証跡は保持します。ガバナンス複雑度レポートは `trackedFiles` を引き続き記録しますが、この値は観測値であり、archive 整合性と現在の Work Item 所有権は hard gate として残ります。

1. `make ai-start TASK=<task> TITLE="..." MODE=code` で Work Item を作成する。
2. Contract の `scope`、`sources`、`acceptance`、`verification`、リスク評価、エージェント能力、実行判断を明確にする。
3. 宣言したスコープ内のみ実装する。
4. Summary に変更ファイル、チェック結果、リスク、レビュー準備、境界チェック、既知ギャップ、破壊的変更を記録する。
5. `make ai-finish TASK=<task>` を実行する。
6. 生成されたステータスとアーカイブ済み Contract/Summary をレビューする。

前置フローで導入準備状況を先に確認したい場合は `make ai-preflight` を実行してください。
このターゲットは助言的な Preflight Review を生成してから検証します。既定では advisory のままで、policy が gate を有効にした場合のみ `needs_human_confirmation` や `not_ready` が失敗になります。
`make generate-ai-preflight-review` は検証を行わずにレポートだけ生成したい場合に使えます。
`make check-ai-preflight-review` は生成済みレポートの構造を検証し、policy が有効な場合のみ gate として動作します。

V2.6.5 では Preflight Review を追加します。原則は **Evidence over Self-Declaration** で、実装可否は AI の自信ではなく Contract の証拠から派生させます。`make ai-start TASK=<task> TITLE="..." MODE=code` と `make ai-preflight` は実装前にこのレビューを表示します。既定では advisory のままで、`needs_human_confirmation` または `not_ready` の場合だけ、エージェントの作業フローは pause してユーザーへ報告します。

`notCodable: true`、`executionDecision.status` が `block` / `defer` / `needs_human_decision`、または実装不可・検証不可・人間判断要求を示す `agentCapability` は、直接 `not_ready` を導く明示的ブロッカーです。

`unknowns` や `notCodable` は失敗ではなく有効な出力です。Summary は監査記録であると同時に協働の引き継ぎです。checkpoint は長いタスクのドリフトを防ぐための環境支援であり、単なる遵守項目ではありません。

`current_status.md` は生成物です。手編集しないでください。

Complexity Policy の変更も同じ境界に従います。提案は policy state が明示的に `confirmed` となり、レビュー証拠が揃うまで有効化しません。予算増加には返済記録を必須とし、記録の欠落や古さは Allow ではなく blocking として扱います。

## 初回導入のショートカット

インストール後の設定は、個別コマンドの羅列ではなく次の 3 フェーズに整理できます。

```sh
make ai-onboard              # 環境 → キャリブレーション → 導入準備
make ai-onboard PHASE=1      # 環境確認のみ
make ai-onboard PHASE=2      # キャリブレーションのみ
make ai-onboard PHASE=3      # 導入準備のみ
```

詳細なチェックリストは [導入準備ガイド](adoption.ja.md) を参照してください。

## ライフサイクルチェック

`make ai-start` は新しい skeleton 作成前にライフサイクル preflight を実行します。アクティブ Contract/Summary が不整合、複数 Work Item が同時アクティブ、`current_status.md` が実状態と不一致の場合は開始を拒否します。
`MODE=code` ではさらに `make ai-preflight` を実行し、実装開始前に Preflight Review を表示します。`needs_human_confirmation` または `not_ready` の場合、エージェントはここで一度停止し、レビュー内容をユーザーへ報告してから実装判断を進めます。

Cockpit Status はレビュアー向けに Preflight Review を見えるままに保ちますが、実装前の pause の代わりにはなりません。

`current_status.md` を生成または検証した後、Work Item を完了せずにライフサイクル状態だけ確認する場合は `make check-ai-status-consistency` を実行します。

アクティブ Work Item が 0 件、または 1 組の Contract/Summary ペアだけの場合、`make repair-ai-status` で `current_status.md` を再生成できます。不整合ファイルや複数アクティブ Work Item の修復は含みません。

archive 後の状態は `no_active_work_item` です。これは worktree が clean である意味ではなく、no-active status はファイル一覧を保存しませんが、worktree change の圧縮信号と ownership preview state は残します。アーカイブ証跡と完全 PR diff の所有権は `make check-ai-pr AI_BASE_COMMIT=<merge-base>` で検証します。`repair-ai-status` は有効な 0 件または 1 組の active 状態だけを再生成し、所有権証跡自体は修復しません。

`make check-ai-diff-ownership` は早期の読み取り専用 Preview です。`AI_BASE_COMMIT` なしでは未追跡ファイルを含むローカル diff を、指定時には PR diff を検査し、PR audit と同じく今回追加された archive pair だけを使用します。PR audit は重複する archive claim を決定的に解決し、最後に有効だった archive pair を採用します。`make ai-pre-merge AI_BASE_COMMIT=<merge-base>` は品質、lifecycle、Preview、最終 PR audit を順に表示し、いずれかが失敗すれば merge 不可です。

## エージェントリスク制御

AI Cockpit はプロンプト指示をガイダンスとして扱い、強制力とはみなしません。リポジトリの安全性は、実際の Work Item と diff を検査するハードゲートから得られます。

既定テンプレートは 3 つの一般的なエージェントリスクを次の制御へ対応付けます。

- プロンプトは助言にすぎない: `make check-ai-agent-risk` が Contract の必須 AI ゲートが verification に含まれ、Summary で passed であることを検証する。
- 作業中のドリフト: `make ai-checkpoint` がスコープ、スコープ外ファイル、unknowns、acceptance、必須チェック状態、レビュー注視点、次アクション、checkpoint メタデータを表示する。
- 不確実性の過大主張: Contract 検証と Agent Risk Guard が unknowns または `notCodable` 状態で非 coding の execution decision を要求する。

Contract の `checkpointPolicy.requiredBeforeFinish` が true の場合、完了前に Summary の `checkpointEvidence` に checkpoint 使用を記録する。

次の概念は分けて扱う:

- `unknowns`: 未解決の事実や設計上の疑問。
- `scenarioCoverage`: verified / unverified / not_applicable で表す既知シナリオ。
- `residualRisks`: 実装後も reviewer が受け入れる残存リスク。
- `followUps`: 現在の Work Item では解決しないが追跡が必要な後続作業。
- `unverifiedScenarios`: 検証未完了のシナリオ名。

## Governance Compression

V2.5 では、Repository Truth が確立された後にもう 1 層が追加されます。V2.6 ではそこに Scenario Coverage が追加されます。

```text
Summary (Repository Truth) → Cockpit (Governance Compression) → Human Decision
```

Cockpit は Summary を複製しません。Contract、Summary、verification の証拠を圧縮して、レビュー担当者や保守者が判断しやすい状態を示します。

`current_status.md` は次の項目を表します。

- `Recommendation`
- `Governance Signals`
- `Evidence`
- `Decision Drivers`

これらの項目は説明可能で保守的であるべきです。証拠が欠けている場合、それを楽観的な結果に置き換えてはいけません。

V2.6 では、中高リスク Work Item 向けに通用的な `Scenario Coverage` 信号が追加されます。`complete`、`incomplete`、`not_required`、`unknown` を区別しますが、release/auth/installer などのシナリオ集を Core に埋め込みません。シナリオ内容は Work Item が保持し、Cockpit は証拠をレビュー向けに圧縮するだけです。

## レビュー準備

Contract の readiness フィールドは、コーディング開始前にエージェントが実装と検証を実行できるかを記録します。Summary の readiness フィールドは残留リスク、期待レビュー注視点、境界チェック、ユーザー修正、既知ギャップ、未検証の主張を記録します。

このテンプレートを他リポジトリへコピーする場合、これらのフィールドは言語中立に保つ。

`.ai/guards/ai_review_policy.yaml` で宣言されたガバナンス機微パスについては `make check-ai-review-policy SUMMARY=<summary.json>` を実行する。このチェックは報告のみで、Summary に `reviewReadiness.expectedReviewFocus` があるかを記録する。

アーカイブ後、PR CI は `make check-ai-pr AI_BASE_COMMIT=<merge-base>` を実行する。インストール済み配布物にはこのターゲットと検証器が含まれる。PR diff 全体の非免除パスは、ちょうど 1 つの変更済みアーカイブペアによって所有されなければならない。Contract の scope 内かつ outOfScope 外であり、対応 Summary に報告されていること。

PR 証跡には Contract version 2 が必要である。version 1 はレガシー読み取り専用で、新規 PR 証跡として導入できない。Contract の承認フィールドは自己申告記録であり、人間 ID の証明ではない。信頼できる承認には保護されたプラットフォームレビューを使い、ガバナンス PR チェックとは独立してプロジェクトテストを実行する。

Summary は Repository Truth、Cockpit は Human Decision State です。Cockpit は事実を増やさず、レビュー可否、ブロック、調査要否を判断するための圧縮された信号だけを示します。
