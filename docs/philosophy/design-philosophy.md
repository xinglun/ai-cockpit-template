---
author: Ray
title: "Design Philosophy"
description: Design philosophy behind AI Cockpit.
keywords:
  - ai-cockpit
  - design-philosophy
  - governance
  - cockpit
---

# 設計思想 (Design Philosophy)

人間の知的生産や開発プロセスが複雑化し、AI エージェントによるコードの自動生成が一般化するにつれ、システム全体の複雑性は人間の直接的な認知限界を超えつつあります。AI Cockpit はこの複雑性を圧縮し、AI エージェントのコード変更に「境界」と「検証可能性」を与えるために設計されました。

本フレームワークの構造は、航空機のフライトプランおよびコックピット計器類と類似しています。これは航空のメタファを無理に当てはめたのではなく、制御問題（Control Problem）を本質から解決しようとした結果、自然と同じ形に収束したものです。

## Design Philosophy

### Discover, Don’t Invent

AI Cockpit は、主観的にプロセスを増やして設計するものではありません。信頼できる人間と AI エージェントの協働（trustworthy human-agent collaboration）が実際に何を必要とするかを観察し、必要な構造を発見します。各コンポーネントは、現実の協働上の必要性へ追跡できなければなりません。

新しい仕組みを「より完全」「より強力」という理由だけで追加してはいけません。それが必要な構造を明らかにしているのか、それとも単にプロセス負荷を増やしているのかを問う必要があります。

Every component exists because the collaboration itself requires it—not because the framework chooses to add complexity.

### Follow the North Star

方向を決める North Star は、Roadmap や機能目標の一覧ではなく、設計判断を安定させる価値の方向です。

**Mission / North Star: Calibrated Human-Agent Trust**

読者向けには、これは **Enable trustworthy collaboration between humans and AI agents** と表現できます。前者がプロジェクトの正式な Mission であり、後者はその方向を理解しやすくした説明です。

Calibrated trust は、エージェントへの信頼を最大化することではありません。証拠が依存を支えるときは依存し、証拠が欠落、古い、矛盾、または不十分なときは、人が調査、介入、または停止を判断できるようにすることです。

### Convergence over Creation

The role of the architect is not to force a solution, but to remove unnecessary complexity until the essential structure becomes visible.

アーキテクトの役割は、解決策を無理に形づくることではなく、本質的な構造が見えるようになるまで、不要な複雑性を取り除くことである。

これは、アーキテクチャに判断や創造がないという意味ではありません。North Star は価値の選択であり、アーキテクチャには判断が必要です。一方、構造は制約、証拠、実践を通じて徐々に現れます。We choose the direction, but we do not prescribe the shape. Direction comes from values; structure emerges through discovery.

### Respect the Nature of the System

人と AI は異なる強み、制約、責任を持ちます。フレームワークは人に機械のような手順実行を要求せず、AI の自信や内部推論を事実として扱いません。

- 人は意図、価値判断、認可、最終責任を担います。
- AI は実行、分析、一貫性チェック、証拠整理に強みを持ちます。

AI Cockpit は協働環境を統治しますが、人の判断を代替しません。AI Cockpit governs evidence; it does not replace evidence-producing tools. これは、AI Cockpit が Agent Runtime、Workflow Engine、Security Sandbox ではなく、Repository Governance Layer であるという境界とも一致します。

### From Philosophy to Structure

Intent、Contract、Verification / Evidence、Guards、Summary、Cockpit Status、Archive は、互いに無関係な機能の集合ではありません。それぞれが、信頼できる人間とエージェントの協働に必要な同じ構造を異なる角度から表現します。

| Element | 表現する協働上の必要性 |
| --- | --- |
| **Intent** | なぜその作業が存在するのか |
| **Contract** | 何を約束し、どこまでを境界とし、どの条件で実行するのか |
| **Verification / Evidence** | どの事実を判断の根拠にするのか |
| **Guards** | 実際の変更が約束から逸脱しないようにすること |
| **Summary** | 結果、理由、検証、残存リスクを保存すること |
| **Cockpit Status** | Repository Truth を人の意思決定に必要な状態へ圧縮すること |
| **Archive** | 監査可能な協働の履歴を保存すること |

この階層は役割を混同しないためのものです。North Star / Mission は **Calibrated Human-Agent Trust**、Design principles は **Discover, Don’t Invent**・**Convergence over Creation**・**Respect the Nature of the System**、Epistemic principle は **Evidence over Self-Declaration**、Mechanism は **Evidence Governance**、Product boundary は **Repository Governance Layer**、Implementation は Intent / Contract / Verification / Summary / Status / Archive です。Discover, Don’t Invent は Evidence over Self-Declaration に取って代わる原則ではなく、異なる層にあります。

## Why AI Cockpit exists

AI Cockpit enables calibrated trust between humans and AI agents through evidence-based governance. Calibrated trust does not mean maximizing trust in an agent. It means enabling humans to rely on the agent when evidence supports reliance and to intervene when evidence is missing, stale, contradictory, or insufficient.

この使命の現在の適用範囲は、ソフトウェアリポジトリにおける human-agent collaboration です。AI Cockpit は汎用 HCI Framework ではありません。HCI の観点では、予測可能性（predictability）、説明可能性（explainability）、説明責任（accountability）、追跡可能性（traceability）を、エージェントの自己申告ではなく、レビュー可能な証拠から支えます。

## Evidence over Self-Declaration

AI Cockpit の中心哲学は **Evidence over Self-Declaration** です。AI Cockpit governs evidence; it does not replace evidence-producing tools.

そのため AI Cockpit は、ガバナンス記録を作成し、委譲された証拠を評価し、その両方を人間の意思決定状態へ圧縮します。

- **Native Governance Evidence**: Intent、Work Item Contract、Verification execution records、AI Change Summary、Cockpit Status、Archive records。これらは AI Cockpit が作成、検証、または保存するガバナンス証拠です。
- **Delegated Domain Evidence**: テスト結果、coverage reports、SBOM、vulnerability scans、provenance、signatures、project-specific quality checks。これらは専門ツールが生成し、AI Cockpit は要求、引用、検証、集約を担います。

SBOM は証拠として扱う成果物です。CycloneDX は SBOM の標準・形式であり、cyclonedx-python-lib、Syft、Trivy、pip-audit、Sigstore tooling などは証拠を生成または処理する交換可能な外部ツール／実装です。これらは AI Cockpit Core の実装ではありません。AI Cockpit リポジトリ自身が公開のために SBOM、scan、provenance を利用することはありますが、それはプロジェクト保守であり、インストール後の Core 製品能力ではありません。Tests と coverage は Release だけに属するのではなく、Work Item Review、Merge、Release の複数の意思決定を支え得ます。

証拠は、支える対象と意思決定に結び付けます。少なくとも Subject（Work Item、Commit、Artifact、または Release）、Decision（Start、Review、Merge、または Release）、Producer、Freshness、Result を明らかにするべきです。これは概念上の evidence attributes であり、現行 Schema に新しい field を定義するものではありません。

Evidence Governance はこの責任境界を実装するメカニズムであり、Repository Governance Layer は現在の製品境界です。Mission は Calibrated Human-Agent Trust、Philosophy は Evidence over Self-Declaration、Implementation は Intent / Contract / Verification / Summary / Status / Archive です。

## 1. 5 つの制御レイヤー

強固な制御システムは、常に以下の独立したレイヤーによって多層防護されます。

| AI 開発における制御課題 | 導入する制御レイヤー | 航空におけるアナロジー |
| --- | --- | --- |
| 開発計画と境界が曖昧 | **Work Item Contract** (契約) | 飛行計画 (Flight Plan) |
| 変更するファイル領域が不明確 | **Scope Guard**（範囲外差分の検出） | 管制空域 (Controlled Airspace) |
| 検証プロセスの省略や形骸化 | **Required Checks** (必須検証) | 計器検査 (Instrument Check) |
| 意思決定プロセスの証跡が残らない | **Change Summary / Archive**（追加式の監査記録） | フライトレコーダー (Black Box) |
| 現在の稼働状態が不透明 | **Cockpit Status** (コックピット) | 計器盤 (Cockpit display) |

---

## 2. 中核となるアーキテクチャ上の決定と背景

AI Cockpit の設計において、なぜ他の手段ではなく現在の形を選択したのか、その技術的合理性を以下に記します。

## Collaborative Environment Design

強い AI エンジニアリング環境は、参加者全員が曖昧な運用期待に完璧に適応することを前提にしません。環境そのものが、人間とエージェントの両方を安定して働かせる必要があります。境界は見えること、委譲は明示されること、不明点は合法的に報告できること、検証は再現可能なチェックへ委譲されること、そしてレビューは事後復元ではなく証拠から始まることが重要です。

AI Cockpit はこの環境設計を、AI Change Governance を中核メカニズムとして実装します。Contract、Checks、Summary、Status、Archive は、単なる監査部品ではなく、協働の前提条件を明示するための構造です。

## 3. Responsibility Model and Review Lenses

AI Cockpit は、内部の思考そのものを保存するのではなく、レビュー可能な証拠を保存します。思考は豊かで文脈依存でよい一方で、レポジトリに残る記録は検証できる形であるべきです。ガバナンスのチェックは private reasoning ではなく、その証拠に対して動きます。

| Layer | Responsibility |
| --- | --- |
| Human Intent | Why the work exists |
| Agent Thinking | How the task is interpreted |
| Reviewable Evidence | What the repository records |
| Repository Governance | What checks and policies validate |
| Repository History | What is preserved for audit and review |

レビューの観点は次の 6 つを使います。これは hard な lifecycle phase ではありません。タスクをどう読むか、どうレビューするかを整理するための lens です。

| Review Lens | AI Cockpit Surface |
| --- | --- |
| Empathy | `problemStatement`, `intent.problem`, `intent.constraints`, `intent.rationale`, `sources` |
| Design | `acceptance`, `guidelines` |
| Architecture | `scope`, `outOfScope`, `riskAssessment`, `rollbackNote` |
| Implementation | `mode`, actual diff, `changedFiles` |
| Judgment | `unknowns`, `notCodable`, `agentCapability`, `executionDecision`, `reviewReadiness` |
| Shipping | `verification`, `Summary`, `Cockpit Status`, `Archive` |

これらは review lenses であり、`Plan -> Scope -> Verify -> Summarize -> Status -> Archive` を置き換えるものではありません。`workflowPhase` や `workflowEvidence` を追加する必要はなく、empathy / design / architecture / implementation / judgment / shipping を必須フィールドにするべきでもありません。

ユーザーが動機や影響を明示していない場合、推測で補わず、`problemStatement` か `unknowns` に `not provided` を明記するほうがよいです。コンテキストが提供されている場合は `intent.problem` に詳細な背景を記述し、`problemStatement` との共存を維持します。


## 4D Operating Model

- Delegation: Work Item Contract と Check ID registry が、作業と検証の担当を明示的に委譲する。
- Description: `scope`、`outOfScope`、`sources`、`acceptance`、`rollbackNote` が、実装前にタスクを記述する。
- Discernment: `unknowns`、`riskAssessment`、`agentCapability`、`executionDecision`、`reviewReadiness` が、判断を可視化する。
- Diligence: required checks、checkpoints、Summary、Status、Archive が、やり切りとレビュー可能性を担保する。

### Q: なぜ CI Action ではなく「Makefile 委譲」なのか？
- **ローカルでの即時フィードバック**: CI サーバーにコードを Push する前に、開発者のローカル環境で AI エージェントが自律的に全チェックを実行して自己修正できる必要があります。
- **言語スタックの中立性**: Contract は Check ID（`projectFormat`、`projectTest` など）を参照し、レジストリが名前空間付き Make ターゲット（`ai-cockpit-project-format-check`、`ai-cockpit-project-test` など）へ解決します。この分離により、共通の Python 制御スクリプトはスタック固有コマンドを直接知る必要がありません。

### Q: なぜ Contract は YAML ではなく「JSON」なのか？
- **厳密なスキーマ検証の容易さ**: Contract は機械が生成し、機械が厳格に読み取ります。YAML はインデントや型推断が曖昧になりがちですが、JSON は仕様が極めてシンプルであり、Python の標準ライブラリ（`json`）のみで安全かつ高速にパースできます。
- **バイト単位の整合性比較**: 現在の Contract ハッシュはファイルの生バイト列から計算するため、空白、インデント、キー順序の変更でも値が変わります。JSON を採用する理由は構文と型の扱いが明確なことであり、整形差を吸収する正規化ハッシュを提供するためではありません。

### Q: なぜ「単一のアクティブ Work Item」に制限するのか？
- **状態の混在防止**: 複数の AI エージェントが並行して異なるタスクの Contract を同時にアクティブにすると、Git 差分がどのタスクの変更範囲に属するのか判別できず、監査の整合性が崩れます。
- **開発プロセスのシングルスレッド化**: 1 つのタスクに集中させ、終了チェックを通過してアーカイブ（`archive-work-item`）した後にのみ次のタスクに着手させることで、開発ブランチの健全性とレビューの追跡性を最大化します。

### Q: なぜ成功した検証結果のみをアーカイブするのか？
- **結果整合性の保証**: 検証済みの Contract/Summary を `.ai/work-items/archive/` へ移し、既存証跡の変更を PR ポリシーで拒否します。これは通常のレビュー経路で追加式の履歴を強制する仕組みであり、ファイルシステムや外部ストレージの不変性を保証するものではありません。

---

## 関連ドキュメント

- [ロードマップ (Roadmap)](../roadmap.md) — V1〜V4 の長期進化方向を定義。本設計思想がその基盤となる。
