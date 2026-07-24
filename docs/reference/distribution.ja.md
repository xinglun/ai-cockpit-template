---
author: Ray
title: "配布"
description: AI Cockpit の配布、整合性検証、インストールオプションを説明する日本語リファレンス。
keywords:
  - ai-cockpit
  - distribution
  - integrity
  - release
---

# 配布

AI Cockpit の配布物は、公開インストーラーとリリースメタデータによってバージョン管理されます。導入フローに含まれないインストーラーオプション、整合性機能、ローカル導入はこのページで確認してください。導入先が非公開または社内ミラーの場合は、ローカルまたは設定済みのソースを使用します。

SBOM と provenance のリリース証拠は、`--source-commit` または `SUPPLY_CHAIN_SOURCE_COMMIT` で明示したソースコミットから生成します。現在の `HEAD` を証拠の識別子に使うことはありません。
コミット済みの `.ai/cockpit/sbom.json`、`provenance.json`、`release-digests.json` は候補ベースラインにすぎません。リリース Workflow は不変の `SOURCE_COMMIT` を checkout した後に `check_supply_chain.py release-assets` を実行し、生成された provenance と digest の subject が同じコミットを指すことを検証し、同じソースコミットに対する厳格な Smoke を通過してから tag と Draft Release を作成します。Draft のまま tag 対象と Asset subject を検証し、`verify_quick_install_release.py` が正確な tag、canonical archive、installer digest、不変の verified capability を検証した場合にだけ公開します。以前のリリース試行向け provenance は現在の最終証明として扱いません。
候補記録は準備時点のスナップショットですが、リリース Workflow は dispatch 時に default branch を再取得し、最新の `SOURCE_COMMIT` を計算します。`source_commit` を省略した場合はその値を使用し、指定した場合は同じ値であることだけを確認します。古い、または不一致の指定は checkout や公開の前に fail closed します。Detached checkout、tag、Workflow、SBOM、provenance、digest はすべて計算された同一の不変コミットを参照しなければなりません。

## PR を起点とするリリース手順

各リリース試行は一つの不変な Identity Tuple を持ちます。`sourceCommit` はマージ済み既定ブランチのコミット、`tagTarget` は同じコミット、`metadataCommit` は候補メタデータを含むコミット（明示必須）、`releaseTag` は要求されたタグです。`HEAD` は証拠として使いません。候補の Freeze メタデータは PR 境界より前にコミットし、マージ後に Workflow が既定ブランチを一度だけ解決して、この Tuple を Preflight、CI 証拠、tag、Provider Asset まで引き継ぎます。close 後のコマンドで Tuple やリリースメタデータを書き換えません。
変更は Pull Request を経由して `main` に入ります。`smoke` と `compatibility` は `main` への push でも実行されます。保守担当者は検証済みの `main` の SHA と新しいタグを指定して `.github/workflows/release.yml` を実行します。Premerge Finalizer は clean な候補 `HEAD` から `sourceTree`、`archiveSha256`、`installerDigest` を生成し、Workflow の Preflight は exact source の `install.sh` を独立に再ハッシュします。ワークフローは既存タグ、ソース SHA、smoke/compatibility の成功、`release.json` を確認してからタグと GitHub Release を作成します。
過去のリリースタグは不変の証拠として扱い、書き換えません。導入先プロジェクトは自身のリモート既定ブランチから導入・アップグレード用ブランチを作成し、公開済みリリースタグを利用します。Candidate PR の準備時スナップショットは、リリースの Source of Truth ではありません。PR のマージ後、Workflow はリモートの既定ブランチを一度だけ解決し、`sourceCommit`、`tagTarget`、`metadataCommit` を同じコミットへ結び付け、依存関係のインストール、Provider CI、tag、公開より前に Release Preflight を実行します。厳格な Smoke は変更前に実行し、tag と Draft Release の作成後は実際の tag に対する Quick Install を通過するまで公開しません。指定された `source_commit` は一致確認のためだけに使い、古い値は fail closed します。作成後に不変タグの不整合が判明した場合、そのタグを移動、削除、再公開しません。関連する GitHub Release を Draft に隔離し、失敗証拠を記録し、Generator と公開前 Gate を Work Item と PR で修正してから、次の Patch Version を訂正版として公開します。
## アーカイブ証拠インデックス

`archive/index.json` は `archive-work-item` が管理する追加型の発見インデックスです。Work Item の識別子、アーカイブ順序、Contract/Summary の相対パス、ファイルハッシュを記録します。アーカイブ済み Contract と Summary が正本であり、インデックスは必要に応じて再生成できます。

開発用 lock は `requirements-dev.in` から `pip-compile --generate-hashes --allow-unsafe` で生成します。すべてのロック済みパッケージには SHA-256 ハッシュを付け、CI は `pip install --require-hashes` でインストールします。`.ai/cockpit/release-digests.json` は lock、SBOM、provenance、インストーラー、リリースメタデータを一つのソースコミットへ結び付けます。
リリース Workflow は compatibility Workflow と同じ固定版の pip-tools bootstrap を clean runner に明示的に導入してから、公開前に `make check-lockfile-reproducibility` を実行します。`requirements-dev.in` から再生成した hash 付き lock とコミット済み lock のバイト列が一致しない場合、tag を変更する前に失敗します。

`releaseEvidenceAuthority` が `release-assets-v1` の場合、公開チェッカーはタグ付き GitHub Release から `sbom.json`、`provenance.json`、`release-digests.json` をダウンロードして再ハッシュし、不変タグツリーと比較します。さらにマニフェストの全成果物を再ハッシュし、期待する成果物一式を要求します。欠落、改ざん、形式不正、タグ不一致、コミット不一致の証拠は、インストーラーを実行する前に拒否されます。

## 公開機能

公開リリースの状態に関する唯一の Canonical Record は `release-state.json`（`schemaVersion: 1`、`canonical: true`）です。状態遷移、リリースタグ、前回リリース、ソース識別子、証拠参照を所有します。`release.json` は公開インストーラー契約、`next-release.json` は未公開 Candidate の投影であり、独立した Release Truth ではありません。自己参照を避けるため `release.json` のソース識別子は不変タグと `release-source.json` の Provider 証拠で検証し、`.gitattributes` はこれらの投影をアーカイブから除外します。`make check-release-state-consistency` は Canonical マーカー、投影先、公開/Candidate タグ、`previousRelease`、Candidate 状態、および旧メタデータの SHA-256 参照が一致することを確認します。

- 公開 Quick Install は不変タグの対象コミット、インストーラーのダイジェスト、`release.json` が宣言するダウンロード可能なリリースアーカイブ Asset と SHA256 を検証し、欠落・不一致なら fail closed します。
- `AI_COCKPIT_TEMPLATE_SHA256` は追加のアサーションであり、公開アーカイブメタデータの代替にはなりません。
- `make check-release-distribution` は実際のインストーラーが配布契約を満たすか確認します。
- 導入先では、テンプレートの SBOM や provenance をそのまま使用せず、プロジェクト固有の証拠を生成します。
- ダイジェストマニフェストはリポジトリ内部の整合性だけを証明します。署名や Sigstore/provenance attestation の代替ではありません。

## インストーラーオプション

```text
--dry-run          書き込まずに実行内容を表示する。
--force            既存の AI Cockpit ファイルを上書きする。
--upgrade          管理対象の実行系、ポリシー、エージェントマーカーをバックアップして置き換える。
--upgrade-with-active
                   active Work Item JSON がある状態で高リスクのアップグレードを許可する。
--replace-glossary プロジェクト所有の .ai/glossary.md を明示的に置き換える。
--create-adoption 最初の監査可能な導入 Work Item を作成する。clean なコミット済み Git 状態が必要。
--with-examples    examples/ を導入先へコピーする。
--update-makefile  導入先の Makefile に "include Makefile.ai" を追加する。
```

`--update-makefile` を使わない場合、インストーラーは `Makefile.ai` と `Makefile.ai.stack` を作成しますが、ホスト側の Makefile は変更しません。

## ローカル導入

```sh
/path/to/ai-cockpit-template/install.sh --stack rust --update-makefile
```

`release-state.json` の `evidenceStatus` は Provider 証拠が保留中、検証済み、公開済みのいずれかを示します。`candidate_prepared` では `evidenceBundleDigest` は `null` のまま許容されますが、`candidate_verified` と `release_published` では実際の 64 桁 SHA-256 が必須です。説明文を digest として受け入れることはなく、状態と digest の組み合わせが不正なら fail closed します。

## このページを使う場面

- 導入ワークフローではなく配布物の動作を確認したい場合。
- インストーラーオプションと整合性機能の正本が必要な場合。
- 保守担当者や統合担当者がリリース固有の配布詳細を記録する場合。
