---
author: Ray
title: "Work Item ライフサイクルのクローズ"
description: Work Item を PR merge 後に安全にクローズする手順を説明する日本語リファレンス。
keywords:
  - ai-cockpit
  - work-item
  - lifecycle
  - closure
---

# Work Item ライフサイクルのクローズ

`make ai-close-work-item` は、PR merge 後の Work Item を閉じ、ブランチと base を安全に整合させる最後の処理です。単に branch を削除するコマンドではありません。

## 前提条件

- Contract と Summary が archive 済みである。
- 対応する PR が merge 済みである。
- Work Item branch が PR と一対一で識別できる。
- PR merge 以降、base branch に予期しない変更がない。
- ローカルとリモートの作業ツリーが clean である。

## 実行

```sh
make ai-close-work-item TASK=<task>
```

コマンドは Contract/Summary/Cockpit Status の archive 証拠、PR の所有権、base の fast-forward-only 同期、local/remote branch の削除、clean worktree、local base と remote base の一致を順に検証します。

## Worktree を使う場合

base branch が別の worktree で checkout されている場合、その worktree の clean 状態を確認してから base を fast-forward します。その後、Work Item worktree を detached にし、local/remote の Work Item branch を削除します。ホスト環境が管理する worktree は、コマンドが所有権を確認せずに削除しません。

## 失敗時の扱い

どれかの事後条件が満たされない場合は fail closed となり、Work Item は閉じたと報告されません。エラーの証拠を確認し、PR、archive、base、worktree の問題を個別に解消してから同じコマンドを再実行してください。`git branch -d` やリモート branch 削除を先に実行すると、PR ownership を検証できなくなるため避けます。

## 完了状態

成功時は次の条件が揃います。

- `active/` に Contract/Summary の組がない。
- archive 証拠が保持されている。
- local base が remote base と一致する。
- Work Item の local/remote branch が削除されている。
- worktree が clean で、次の Work Item を開始できる。
