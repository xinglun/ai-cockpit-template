---
author: Ray
title: "実フィクスチャ証拠"
description: "フィクスチャ実験におけるライフサイクル事実と証拠境界。"
keywords:
  - lifecycle
  - evidence
---

`make ai-lifecycle-facts` は、Bootstrap、Calibration、Governed Development、No Active Work Item の状態を機械可読 JSON として出力します。これは読み取り専用の観測であり、`readiness` と `enterpriseAssurance` は `not_claimed`、プロバイダー資産と外部エンタープライズ保証は `not_run` のままです。ローカルのフィクスチャ実行結果からセキュリティ、コンプライアンス、本番準備を推論してはいけません。
