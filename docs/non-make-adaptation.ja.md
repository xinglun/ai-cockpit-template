---
author: Ray
title: "Make 以外のビルドシステム適応"
description: npm scripts、just、task など Make 以外のエントリポイントから AI Cockpit を橋渡しするガイド。
---

# Make 以外のビルドシステム適応

AI Cockpit のガバナンス runtime は Python 標準ライブラリと GNU Make を前提とします。アプリケーションのビルドシステムが npm scripts、just、task、mage など Make 以外でも、**品質ゲートだけ** Makefile へ委譲することで統合できます。

## 基本方針

1. リポジトリ root に `Makefile.ai` を include した薄い `Makefile` を置く。
2. `Makefile.ai.stack` の `PROJECT_FORMAT_CHECK`、`PROJECT_TEST`、`PROJECT_LINT` を既存コマンドへ向ける。
3. Contract の verification は引き続き Check ID のみを使い、任意 shell を Contract に直接書かない。

```makefile
include Makefile.ai

PROJECT_FORMAT_CHECK = npm run format:check
PROJECT_TEST = npm run test
PROJECT_LINT = npm run lint
```

上記 3 変数は `Makefile.ai.stack` に置くのが既定です。プロジェクトによっては root `Makefile` 側で `-include Makefile.ai.stack` より前に export しても構いません。

## npm / pnpm / bun scripts

Node 中心リポジトリでは、package.json の scripts をそのまま橋渡しします。

```makefile
# Makefile.ai.stack（typescript 設定をベースに編集）
PROJECT_FORMAT_CHECK = npm run format:check
PROJECT_TEST = npm run test
PROJECT_LINT = npm run lint
```

pnpm や bun を使う場合は `npm run` を `pnpm` / `bun run` に置き換えます。CI でも同じ Make ターゲット `make ai-cockpit-quality` を呼ぶことで、ローカルと CI の入口を一致させます。

## just / task ランナー

justfile や Taskfile がある場合、Make は薄いファサードに留めます。

```makefile
# just を使う例
PROJECT_FORMAT_CHECK = just format-check
PROJECT_TEST = just test
PROJECT_LINT = just lint
```

```makefile
# go-task を使う例
PROJECT_TEST = task test
PROJECT_LINT = task lint
PROJECT_FORMAT_CHECK = task fmt-check
```

just / task 側に `ai-cockpit-quality` 相当の aggregate ターゲットを作っても構いませんが、AI Cockpit の Contract と `checks.yaml` は **Make ターゲット名** を参照する設計のままです。aggregate は `Makefile.ai.stack` 内の 3 変数から呼び出してください。

## .NET dotnet CLI 中心プロジェクト

csharp 設定は `dotnet format`、`dotnet test`、`dotnet build` を前提とします。solution パスが非標準の場合はこの設定を編集します。

```makefile
PROJECT_FORMAT_CHECK = dotnet format Smoke.sln --verify-no-changes
PROJECT_TEST = dotnet test Smoke.sln --no-build
PROJECT_LINT = dotnet build Smoke.sln --no-restore
```

solution 名やプロジェクト layout はリポジトリごとに異なるため、導入時は `make cockpit-doctor` と Coverage Guard の calibration を必ず実行してください。

## monorepo

monorepo では品質コマンドを workspace root に集約するか、サブパッケージごとに Make 変数を切り替えます。

```makefile
PROJECT_TEST = npm run test --workspaces
PROJECT_LINT = npm run lint --workspaces
PROJECT_FORMAT_CHECK = npm run format:check --workspaces
```

Coverage Guard と Scope Guard の glob は `.ai/guards/coverage_policy.yaml` と Project Profile でリポジトリ layout に合わせて調整します。既定 pattern は出発点であり、monorepo 向けの完成形ではありません。

## 導入時の推奨手順

1. 既存 stack 設定（`typescript`、`csharp` など）を `--stack` でインストールする。
2. `Makefile.ai.stack` の 3 変数だけを既存ランナーへ差し替える。
3. `make ai-onboard` で環境、キャリブレーション、readiness を確認する。
4. `make ai-cockpit-quality` が成功してから `configure_ai_cockpit` Work Item を完了する。

## 制約

- AI Cockpit 本体の `make ai-start`、`make ai-finish`、`make check-ai-pr` などは GNU Make が必要です。
- Windows ネイティブ shell はサポート対象外です。WSL など POSIX 環境を使用してください。
- Make を完全に排除することはできません。排除したい場合は、CI だけ WSL/Linux runner で Make を実行し、開発者ローカルは just/task から同等コマンドを呼ぶハイブリッド構成が現実的です。
