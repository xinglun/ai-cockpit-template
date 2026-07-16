---
author: Ray
title: "アップグレード"
description: 既存の AI Cockpit 導入を更新するための日本語リファレンス。
keywords:
  - ai-cockpit
  - upgrade
  - migration
  - release
---

# アップグレード

対象リポジトリに AI Cockpit のファイルがすでにあり、管理対象の実行系、ポリシー、マーカーファイルを更新する場合は `--upgrade` を使います。アップグレードは導入先プロジェクトの独立した Work Item と専用ブランチで行い、リモート、既定ブランチ、base commit、対象 release tag を Contract に記録します。

```sh
CURRENT_VERSION="${CURRENT_VERSION:?set CURRENT_VERSION to the installed release tag}"
TARGET_VERSION="${TARGET_VERSION:?set TARGET_VERSION to a newer release tag}"
test "$TARGET_VERSION" != "$CURRENT_VERSION"
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL "${AI_COCKPIT_TEMPLATE_RAW_BASE:?set AI_COCKPIT_TEMPLATE_RAW_BASE to the matching raw-content base}/$TARGET_VERSION/install.sh" -o "$INSTALLER"
AI_COCKPIT_TEMPLATE_REPO="${AI_COCKPIT_TEMPLATE_REPO:?set AI_COCKPIT_TEMPLATE_REPO to the release source}" \
AI_COCKPIT_TEMPLATE_REF="$TARGET_VERSION" \
  sh "$INSTALLER" --upgrade --stack rust
```

実際のリリースソースに合わせて例のリポジトリを置き換えてください。ミラーまたは非公開配布を更新する場合は、公開例ではなく設定済みソースを指定します。

インストーラーは配布物、Contract schema、release semver の downgrade を拒否します。`TARGET_VERSION` を `.ai/cockpit/version.json` に記録された semver より低くしないでください。

既定では `.ai/work-items/active/` に Work Item JSON があると書き込み前に停止します。先に active task を finish/archive してください。`--upgrade-with-active` は、タスク中にガバナンス意味論を変更する必要がある復旧時だけ使う high-risk override です。

置換前に管理対象ファイルは `.ai/cockpit/upgrade-backups/<timestamp>/` へコピーされます。既存の Makefile へ追記する初回導入でも、このディレクトリは transaction rollback 用に使われます。成功したアップグレードのバックアップは不要になったらレビュー後に削除してください。

`--update-makefile` を使わなかった場合は、プロジェクトの Makefile に次を追加します。

```make
include Makefile.ai
```

インストーラーオプションは [配布](distribution.ja.md)、失敗からの復旧は [トラブルシューティング](troubleshooting.ja.md) を参照してください。

## Cursor rule の既定値

新規導入の `.cursor/rules/ai-cockpit.mdc` は `alwaysApply: false` です。読み取り専用調査にも Work Item を強制したいチームは、ローカルの影響を確認したうえで Cursor の **Always Apply** を有効にするか、`alwaysApply: true` を設定します。既存導入では upgrade または管理対象 `.cursor` ツリーの merge まで現在の rule が保持されます。
