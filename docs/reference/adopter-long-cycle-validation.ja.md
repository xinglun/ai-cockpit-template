---
author: Ray
title: "Adopter 長周期検証"
description: "複数スタックと独立 Adopter リポジトリの長周期証拠境界。"
keywords:
  - adopter
  - lifecycle
  - validation
---

# Adopter 長周期検証
`make cross-stack-long-cycle` は、Python と Java の依存なしフィクスチャ、TypeScript の npm ライフサイクルテスト、独立 Adopter Git リポジトリの Upgrade/Rollback/Branch Cleanup をまとめた証拠を生成します。Java フィクスチャは二つのモジュールを `javac`/`java` で実行し、一時的な Upgrade/Rollback 比較を行います。各段階の `executionKind` は `local_real_execution`、`blocked`、`not_run` を明示し、Manifest Simulation を実行証拠として扱いません。Install、Configure、Normal Work Item、Ambiguous Request、Critical Domain Change、Upgrade、Rollback、Release Check の各段階を記録し、blocked 段階には再開条件を付けます。Provider と Identity は `not_run`、Enterprise Assurance は `not_claimed` のままです。
