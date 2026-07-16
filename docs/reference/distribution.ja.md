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

コミット済みの `.ai/cockpit/sbom.json`、`provenance.json`、`release-digests.json` は候補ベースラインにすぎません。リリース Workflow は不変の `SOURCE_COMMIT` を checkout した後に `check_supply_chain.py release-assets` を実行し、生成された provenance と digest の subject が同じコミットを指すことを検証してから、GitHub Release Asset として公開します。以前の公開リリース向けに生成された provenance は、現在のリリースの最終証明として扱いません。

## PR を起点とするリリース手順

変更は Pull Request を経由して `main` に入ります。`smoke` と `compatibility` は `main` への push でも実行されます。保守担当者は検証済みの `main` の SHA と新しいタグを指定して `.github/workflows/release.yml` を実行します。ワークフローは既存タグ、ソース SHA、smoke/compatibility の成功、`release.json` を確認してからタグと GitHub Release を作成します。

過去のリリースタグは不変の証拠として扱い、書き換えません。導入先プロジェクトは自身のリモート既定ブランチから導入・アップグレード用ブランチを作成し、公開済みリリースタグを利用します。

## アーカイブ証拠インデックス

`archive/index.json` は `archive-work-item` が管理する追加型の発見インデックスです。Work Item の識別子、アーカイブ順序、Contract/Summary の相対パス、ファイルハッシュを記録します。アーカイブ済み Contract と Summary が正本であり、インデックスは必要に応じて再生成できます。

開発用 lock は `requirements-dev.in` から `pip-compile --generate-hashes --allow-unsafe` で生成します。すべてのロック済みパッケージには SHA-256 ハッシュを付け、CI は `pip install --require-hashes` でインストールします。`.ai/cockpit/release-digests.json` は lock、SBOM、provenance、インストーラー、リリースメタデータを一つのソースコミットへ結び付けます。

## 公開機能

公開リリースの定義は `release.json` にあります。

- `AI_COCKPIT_TEMPLATE_SHA256` を指定した場合、公開インストーラーアーカイブを検証できます。
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

## このページを使う場面

- 導入ワークフローではなく配布物の動作を確認したい場合。
- インストーラーオプションと整合性機能の正本が必要な場合。
- 保守担当者や統合担当者がリリース固有の配布詳細を記録する場合。
