---
author: Ray
title: "Glossary"
description: AI Cockpit の主要用語とアーキテクチャ境界の定義。
---

# AI Cockpit 用語集

この文書は、このリポジトリで使用するガバナンス用語を定義します。実装前に確認し、Contract、Summary、ドキュメント、およびコードで一貫した名称を使用してください。

## 主要用語

| 用語 | 定義 |
| --- | --- |
| Intent | タスクが存在する理由を宣言する一級ガバナンスオブジェクト。problem（問題の詳細）、constraints（制約）、rationale（根拠）などを含む（全フィールドは任意）。Contract に先行し、Contract を駆動する。 |
| Work Item Contract | 変更前に scope、outOfScope、sources、acceptance、verification、および実行可否を宣言する JSON 記録。Intent に基づいて作成される。 |
| AI Change Summary | 変更内容、検証結果、ガイドライン準拠、残存リスク、および Intent Alignment を記録する JSON 記録。Intent への整合性を検証する。 |
| Intent Alignment | Summary における Intent 達成度の検証。problemResolved、constraintsRespected、nonGoalsAvoided、rationaleValidated などを含む。 |
| Governance Loop | Intent → Contract → Implementation → Verification → Summary の完全なガバナンス閉ループ。V2 では Intent Alignment を含み、V2.5 では Cockpit への圧縮に接続される。 |
| Repository Truth | Summary によって表現される、変更・検証・リスク・整合性に関するリポジトリ上の事実。 |
| Governance Compression | Repository Truth を人間の意思決定に必要な最小シグナルへ圧縮する層。V2.5 で導入され、V2.6 では Scenario Coverage を含む。Summary を複製せず、決定に必要な証拠だけを提示する。 |
| Preflight Review | Work Item Contract の既存証拠から implementation 前の readiness を派生する助言的ビュー。AI の自己申告ではなく、Intent / Unknowns / Sources / Acceptance / Scope / OutOfScope / Scenario Coverage / Verification を根拠にする。`notCodable: true`、`executionDecision` の block/defer/needs_human_decision、または実装/検証不可・人間判断要求の `agentCapability` は直接 `not_ready` を導く。 |
| Preflight Pause Rule | Preflight Review が `needs_human_confirmation` または `not_ready` の場合に、AI がユーザーへレビューを報告してから実装判断を続けるべきというワークフロー規則。コマンドの exit code とは独立する。 |
| Scenario Coverage | 中高リスク Work Item で、どのリスクドメインのシナリオが verified / unverified / not_applicable なのかを示す通用的な証跡。シナリオ内容は Core ではなく Work Item が持つ。 |
| Scenario Coverage Guard | `scenarioCoverage` の構造と、riskAssessment に応じた必須性を検証するガード。 |
| Human Decision State | Cockpit が示す、人間が review / merge / block / investigate を判断するための状態。 |
| Governance Signals | Cockpit が出力する圧縮済みの判断信号。Intent、Acceptance、Unknowns、Verification、Scenario Coverage、Guidelines、Checkpoints、Residual Risk などを含む。 |
| Recommendation | Cockpit が導出する推奨判定。例: ready_for_review、ready_with_risks、needs_investigation、blocked。 |
| Active Work Item | `.ai/work-items/active/` に Contract と Summary の組が存在する、作業中の項目。 |
| Archived Work Item | 検証後に `.ai/work-items/archive/` へ移動された Contract と Summary の監査記録。 |
| Scope Guard | 実際の差分が Contract の scope 内かを検証する仕組み。 |
| Check ID | `.ai/cockpit/checks.yaml` に登録された、Contract から参照可能な検証項目の識別子。 |
| Cockpit Status | Active Work Item の状態を示す生成ファイル。V2.5 では Recommendation、Governance Signals、Evidence、Decision Drivers を含む。V2.6 では Scenario Coverage 信号も表現する。手動では編集しない。 |
| no_active_work_item | active Contract/Summary が存在しない安定状態。アーカイブ中の瞬時の Git diff は生成済み status に保存せず、no-active status は決定的な clean marker を残す。ローカルの差分確認は `make check-ai-diff-ownership`、アーカイブ済み証跡と完全 PR diff の帰属は `make check-ai-pr AI_BASE_COMMIT=<merge-base>` が決め、重複する archive claim は最後に有効だった pair を採用する。 |
| Repository Governance Layer | AI Cockpit の現在の製品境界。Agent Runtime、Workflow Engine、Security Sandbox ではなく、AI-assisted software development におけるリポジトリレベルのガバナンス、コンテキスト、検証、監査可能性を提供する。実装メカニズムは Evidence Governance であり、最終使命は Calibrated Human-Agent Trust。V2.5 では Human Decision State の圧縮が加わり、V2.6 では Scenario Coverage が追加される。 |
| Evidence over Self-Declaration | 実装可否や readiness を AI の自己申告ではなく、Contract や Summary に残された証拠から派生させる原則。Preflight Review の判断基準になる。 |
| Calibrated Trust | エージェントへの信頼を最大化することではなく、証拠が依存を支えるときに依存し、証拠が欠落、古い、矛盾、または不十分なときに人が調査・介入・停止を判断できる状態。AI Cockpit の使命は calibrated human-agent trust を支えること。 |
| Evidence Governance | AI Cockpit がガバナンス記録を作成し、委譲された証拠を要求・引用・検証・集約し、その両方を Human Decision State へ圧縮するメカニズム。 |
| Native Governance Evidence | AI Cockpit が作成、検証、または保存する Intent、Work Item Contract、verification execution records、AI Change Summary、Cockpit Status、Archive records。 |
| Delegated Domain Evidence | 専門の evidence-producing tools が生成し、AI Cockpit が要求、引用、検証、集約する test results、coverage reports、SBOM、vulnerability scans、provenance、signatures、project-specific quality checks。 |
| Evidence-Producing Tool | ドメイン固有の結果や成果物を生成・処理する専門ツールまたは実装。SBOM は証拠成果物、CycloneDX は標準・形式であり、cyclonedx-python-lib、Syft、Trivy、pip-audit、Sigstore tooling などが交換可能な外部ツール／実装に当たる。AI Cockpit Core の実装ではない。 |
| Release Evidence | Release の判断を支える Delegated Domain Evidence。SBOM、vulnerability scan、provenance、signatures などを含むが、AI Cockpit Core の能力そのものではない。Tests と coverage は Work Item Review、Merge、Release の複数の判断を支え得る。 |

## アーキテクチャ境界

- `scripts/`: Python 標準ライブラリを中心とするガバナンス実行系。
- `.ai/cockpit/`: check catalog、生成 status、および workflow の説明。
- `.ai/guards/`: scope、ownership、boundary、backtrack、coverage、および review policy の設定。
- `templates/`: インストール先へ配布するルール、glossary、および stack preset。
- `examples/`: 一部の stack 向け設定例。全 preset の動作保証一覧ではない。
