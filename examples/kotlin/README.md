---
author: Ray
title: "Kotlin Adaptation Example"
description: Kotlin stack adaptation example for AI Cockpit.
keywords:
  - kotlin
  - ai-cockpit
  - ai-agents
  - governance
---

# Kotlin Adaptation Example

## 1. インストール

```sh
: "${AI_COCKPIT_TEMPLATE_REF:?set AI_COCKPIT_TEMPLATE_REF to the release tag}"
: "${AI_COCKPIT_TEMPLATE_RAW_BASE:?set AI_COCKPIT_TEMPLATE_RAW_BASE to the matching raw-content base}"
sh -c "$(curl -fsSL "${AI_COCKPIT_TEMPLATE_RAW_BASE}/${AI_COCKPIT_TEMPLATE_REF}/install.sh")" -- --stack kotlin --update-makefile --create-adoption
```

## 2. 品質ゲートとガード設定

Gradle ベースの Kotlin リポジトリでは、`Makefile.ai.stack` に次のスタックプリセットを設定します。

```make
PROJECT_FORMAT_CHECK = ./gradlew spotlessCheck
PROJECT_TEST = ./gradlew test
PROJECT_LINT = ./gradlew check
```

`.ai/guards/coverage_policy.yaml` には、次のガードパターンを推奨します。

```yaml
production:
  include:
    - "src/main/kotlin/**"
  exclude:
    - "src/test/**"

tests:
  include:
    - "src/test/**"
```

---

## 3. 実践的な Kotlin 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な Kotlin 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_user_service",
  "mode": "code",
  "scope": [
    "build.gradle.kts",
    "src/main/kotlin/com/example/service/UserService.kt",
    "src/test/kotlin/com/example/service/UserServiceTest.kt"
  ],
  "guidelines": [
    "すべてのビジネスロジック関数には KDoc コメントを記述すること"
  ],
  "verification": [
    { "check": "aiWorkItem", "required": true },
    { "check": "aiScope", "required": true },
    { "check": "aiGuards", "required": true },
    { "check": "aiCheckpoint", "required": true },
    { "check": "aiAgentRisk", "required": true },
    { "check": "aiReviewPolicy", "required": true },
    { "check": "aiBacktrack", "required": true },
    { "check": "aiCoverage", "required": true },
    { "check": "aiScenarioCoverage", "required": true },
    { "check": "aiGuidelines", "required": true },
    { "check": "aiSummary", "required": true },
    { "check": "aiStatus", "required": true },
    { "check": "aiStatusCheck", "required": true },
    { "check": "aiStatusConsistency", "required": true },
    { "check": "aiDiffOwnership", "required": true },
    { "check": "quality", "required": true }
  ]
}
```

---

## 4. guidelinesCompliance の記述例 (`*.summary.json` 抜粋)

上記ガイドラインに適合したことを証明する要約（Summary）の記述例です。

```json
{
  "guidelinesCompliance": [
    {
      "guideline": "すべてのビジネスロジック関数には KDoc コメントを記述すること",
      "compliant": true,
      "evidence": "UserService.kt 内のメソッドに KDoc コメントを追記しました。"
    }
  ]
}
```
