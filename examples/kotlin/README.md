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
AI_COCKPIT_TEMPLATE_REF=v0.5.11 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.11/install.sh)" -- --stack kotlin --update-makefile --create-adoption
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
    { "check": "aiGuidelines", "required": true },
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
