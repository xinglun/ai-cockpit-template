---
author: Ray
title: "Local Calibration Template Improvements"
description: sej_ios 導入検討から得た教訓に基づく、テンプレート側の改善計画と開発者向け指示。
keywords:
  - ai-cockpit
  - adoption
  - local-calibration
  - swift
  - ios
  - template
---

# ローカルキャリブレーション型導入 — テンプレート改善計画

## 1. 背景

大規模なレガシー Native iOS リポジトリ（CocoaPods + Xcode workspace、単体テスト極少、GitLab CI は build/deploy のみ）への AI Cockpit v0.5.14 導入可否を検討した。その結果、**インストール自体は可能**だが、**开箱即用ではない**。成功の鍵はテンプレートをプロジェクト専用化することではなく、**導入後のローカルキャリブレーション Work Item** にある。

本ドキュメントは、その経験を一般化し、テンプレートリポジトリ側で実施すべき改善を優先度付きで整理する。プロジェクト固有 preset（例: sej_ios 専用 stack）は **スコープ外** とする。

## 2. 経験要約（教訓）

| 観点 | 事実 | 示唆 |
| --- | --- | --- |
| ツールチェーン | Git / Python 3.10+ / Make / xcodebuild は充足 | インストール blocker ではない |
| `--create-adoption` | clean worktree 必須 | tracked な `.DS_Store` 等は導入前に衛生処理 |
| `STACK=swift` | preset は SPM 向け（`swift test`） | CocoaPods 工程では preset を「起点」として扱い、キャリブレーション必須 |
| README「verified」 | `mobile-stack-quality` は最小 SPM fixture のみ | 「Swift verified ≠ Xcode/CocoaPods 検証済み」と明記すべき |
| `cockpit-doctor` | 固定ディレクトリ名（`Sources/`、`Tests/`）のみ検出 | `*Tests/`、`Podfile`、`.xcodeproj` 非検出 → blocking unknowns が増える |
| Coverage Guard | デフォルト `*.swift` は広い | レガシー工程では `reportOnly: true` + パス絞り込みが前提 |
| CI | `GIT_DEPTH: 1` では `check-ai-pr` 不十分 | フル履歴 fetch が別途必要 |
| Cursor rule | `alwaysApply: true` | 導入チームは Phase B でローカル調整を検討 |
| 成功モデル | 2 段 commit（adopt → configure） | テンプレート文書で標準フローとして強調 |

## 3. 設計原則（変更の境界）

テンプレート改善は次の原則に従う。

1. **汎用性維持**: 単一顧客・単一リポジトリ向け preset や hardcode を追加しない。
2. **導入とキャリブレーションの分離**: Installation / Adoption / Project Calibration の 3 段階を崩さない。
3. **fail closed のまま**: 未キャリブレーション状態で quality / Coverage を黙って通さない。
4. **検出の強化は可、命令の自動化は不可**: doctor が事実を報告する。`xcodebuild` 引数の自動生成はしない。
5. **段階的 CI**: 文書・例では `check-ai-pr`（L1）と `ai-cockpit-quality`（L2）の分離を推奨する。

## 4. 改善計画（優先度）

### Phase A — ドキュメント整合（P0、低リスク）

**目的**: 誤解を減らし、ローカルキャリブレーションを公式パスとして明示する。

| ID | 作業 | 対象ファイル | 完了条件 |
| --- | --- | --- | --- |
| A-1 | Swift stack の適用範囲を SPM と明記し、Xcode/CocoaPods は **Project Calibration 必須** と書く | `templates/stacks/swift.mk`（コメント）、`examples/swift/README.md`、`docs/getting-started/installation.md` | 「verified」の脚注または表で mobile-stack-quality = SPM fixture と記載 |
| A-2 | レガシー / モバイル Native 向け **ローカルキャリブレーション checklist** を追加 | `docs/getting-started/installation.md` または `.ai/cockpit/adoption.md` | adopt → configure の 2 Work Item、L1/L2 CI、Coverage 初期 `reportOnly` を checklist 化 |
| A-3 | `STACK=generic` を CocoaPods 等で preset が misleading な場合の推奨オプションとして記載 | `docs/getting-started/installation.md`、`README.md` | generic 選択時の UX（明示的 configure エラー）を 1 段落で説明 |
| A-4 | GitLab CI 最小 snippet（`GIT_DEPTH: 0` + `check-ai-pr`） | `docs/getting-started/installation.md` または `docs/reference/distribution.md` | GitHub 偏重を補完；quality job は optional コメント付き |

**開発者指示（Phase A）**

- 新規 stack を増やさない。
- 既存 installation フローの段階番号を変えない。
- 文言はプロジェクト中立（sej_ios 固有名称を本文に入れない）。
- 変更後 `make check-docs-metadata` および関連 doc テストを通す。

---

### Phase B — Project Doctor 拡張（P1、中リスク）

**目的**: 非標準ディレクトリ layout でも **read-only 事実** を増やし、キャリブレーション入力を改善する。

| ID | 作業 | 対象ファイル | 完了条件 |
| --- | --- | --- | --- |
| B-1 | BUILD 信号に `Podfile`、`*.xcodeproj`、`*.xcworkspace`（存在時）を追加 | `scripts/ai_project_doctor.py` | doctor report に evidence 付きで出力 |
| B-2 | テスト根候補に `*Tests` サフィックスディレクトリの走査を追加（浅い glob、性能に配慮） | `scripts/ai_project_doctor.py` | `FooTests/` 型を testRoots 候補として提案 |
| B-3 | 生産根候補に `*.xcodeproj`  sibling の主要ソースディレクトリヒューリスティック（任意・保守的） | `scripts/ai_project_doctor.py` | マッチ時のみ medium confidence で提案；不明は unknowns に残す |
| B-4 | doctor 出力の unknowns が **自動承認されない** ことをテストで固定 | `tests/test_doctor.py` | 新信号の unit test；blocking 判定ロジックは変更しない |

**開発者指示（Phase B）**

- doctor は **提案のみ**。Guard YAML や `Makefile.ai.stack` を自動書き換えしない。
- glob はリポジトリ root 限定・深さ制限付きとし、巨大 monorepo での性能劣化を避ける。
- 既存 Flutter / SPM 検出の regression test を維持する。

---

### Phase C — 中立な適応例の拡充（P2、低〜中リスク）

**目的**: 専用 stack なしで、Xcode 系の **手動キャリブレーション例** を提供する。

| ID | 作業 | 対象ファイル | 完了条件 |
| --- | --- | --- | --- |
| C-1 | `examples/swift/README.md` に「Xcode / workspace 適応」節を追加 | `examples/swift/README.md` | `xcodebuild test -workspace`、`-configuration`、事前 `pod install` を中立例として記載 |
| C-2 | Coverage Guard の **Xcode 向け include/exclude 例**（`Pods/**` 除外等）を example のみに記載 | `examples/swift/README.md` | テンプレート本体 `coverage_policy.yaml` の default は広いまま維持 |
| C-3 | `configure_ai_cockpit` Contract scope 例に GitLab CI を明示 | `docs/getting-started/installation.md` | 既存 scope リストに `.gitlab-ci.yml` が含まれることを再確認・補強 |

**開発者指示（Phase C）**

- `examples/` は illustrative。インストール時にコピーされないことを README で維持。
- 例中のプロジェクト名はプレースホルダ（`MyApp`）のみ。

---

### Phase D — オプション改善（P3、要判断）

| ID | 作業 | 判断基準 |
| --- | --- | --- |
| D-1 | Cursor rule デフォルトを `alwaysApply: false` に変更 | 導入フィードバックが「調査のみでも Work Item 強制」と多数の場合のみ |
| D-2 | インストール前 preflight（dirty + tracked-ignored 警告） | `--create-adoption` 失敗 support コストが高い場合 |
| D-3 | `mobile-stack-quality` に Xcode fixture 追加 | CI 時間・メンテコストと相談；**SPM-only 明記で足りるなら D-3 は見送り** |

**開発者指示（Phase D）**

- D-1 は breaking UX change。minor release note と adoption 文書更新が必須。
- D-2/D-3 は Phase A〜C の効果測定後に着手。

## 5. スコープ外（明示的にやらないこと）

- sej_ios / seveneleven 等、特定リポジトリ名の preset や Makefile 断片のテンプレート同梱
- `ios-cocoapods` 等の新 stack 追加（原則）。中立 example で代替
- インストール時の `pod install` や `xcodebuild` の自動実行
- Coverage Guard デフォルトをレガシー向けに狭める（プロジェクトキャリブレーションに委ねる）
- 未キャリブレーション工程で `adoptionReviewed: true` を自動設定

## 6. 採用側（ターゲットリポジトリ）への標準指示

テンプレート改善と独立し、**すべての採用リポジトリ** に共通する手順。サポート文書として installation にリンク可能。

```text
Phase 0  導入前: git worktree clean、tracked ignore ファイルの整理
Phase 1  インストール: STACK=generic または swift + --create-adoption
Phase 2  Adoption: make ai-finish TASK=adopt_ai_cockpit → 単独 commit
Phase 3  Calibration: configure_ai_cockpit Work Item
         - Makefile.ai.stack（プロジェクト品質コマンド）
         - .ai/guards/coverage_policy.yaml（reportOnly → 段階的 blocking）
         - .ai/project_profile.yaml（境界承認）
         - CI L1: check-ai-pr のみ → 安定後 L2: ai-cockpit-quality
Phase 4  试点 Work Item（quality optional 可）→ 本番ゲート化
```

## 7. 検証計画（テンプレート側）

| Phase | 必須 verification |
| --- | --- |
| A | `make check-docs-metadata`、関連 doc unit tests |
| B | `pytest tests/test_doctor.py`、必要なら `make cockpit-doctor` を fixture repo で smoke |
| C | doc metadata、example README front matter |
| D | 該当変更ごとに installer / adoption e2e |

リリース前: 既存 `make check-ai-pr` と template 自身の governance checks を regression として維持。

## 8. マイルストーン案

| マイルストーン | 含む Phase | 想定 |
| --- | --- | --- |
| M1 ドキュメント整合 | A | 1 PR、パッチ release 可 |
| M2 Doctor 拡張 | B | 1 PR + tests |
| M3 適応例 | C | 1 PR、M1 と同梱可 |
| M4 オプション | D | 別 epic、要 product 判断 |

## 9. 関連資料

- [Installation](../getting-started/installation.md)
- [Adoption Readiness](../../.ai/cockpit/adoption.md)
- [Swift Adaptation Example](../../examples/swift/README.md)
- [Design Philosophy](../philosophy/design-philosophy.md)
