---
author: Ray
title: "Java Adaptation Example"
description: Java stack adaptation example for AI Cockpit.
keywords:
  - java
  - ai-cockpit
  - ai-agents
  - governance
---

# Java Adaptation Example

## 1. インストール

```sh
AI_COCKPIT_TEMPLATE_REF=v0.5.3 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.3/install.sh)" -- --stack java --update-makefile --create-adoption
```

## 2. 品質ゲートとガード設定

Gradle ベースの Java リポジトリでは、`Makefile.ai.stack` に次のスタックプリセットを設定します。

```make
PROJECT_FORMAT_CHECK = ./gradlew spotlessCheck
PROJECT_TEST = ./gradlew test
PROJECT_LINT = ./gradlew check
```

Spring Boot 向けの `.ai/guards/coverage_policy.yaml` には、次のガードパターンを推奨します。

```yaml
production:
  include:
    - "src/main/**"
  exclude:
    - "**/*Test.java"     # JUnit テストクラス（Test で終わる）
    - "**/*Tests.java"    # JUnit テストクラス（Tests で終わる）
    - "**/*Spec.java"     # Spock など
    - "**/*IT.java"       # 結合テスト（Integration Test）

tests:
  include:
    - "src/test/**"
    - "**/*Test.java"
    - "**/*Tests.java"
    - "**/*Spec.java"
    - "**/*IT.java"
```

Android 向けの `.ai/guards/coverage_policy.yaml` には、次のガードパターンを推奨します。

```yaml
production:
  include:
    - "app/src/main/**"   # app モジュール
    - "*/src/main/**"     # マルチモジュール構成対応
  exclude:
    - "**/*Test*.kt"
    - "**/*Test*.java"
    - "**/*Spec*.kt"

tests:
  include:
    - "app/src/test/**"          # ローカル単体テスト
    - "app/src/androidTest/**"   # 結合テスト（インストルメント）
    - "**/*Test*.kt"
    - "**/*Test*.java"
```

---

## 3. 実践的な Java 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な Java 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_user_controller",
  "mode": "code",
  "scope": [
    "build.gradle",
    "src/main/java/com/example/controller/UserController.java",
    "src/test/java/com/example/controller/UserControllerTest.java"
  ],
  "guidelines": [
    "すべての新規コントローラークラスには Javadoc を記述すること",
    "テストカバレッジの警告が発生しないよう、対応するテストクラスを必ず同行させること"
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
      "guideline": "すべての新規コントローラークラスには Javadoc を記述すること",
      "compliant": true,
      "evidence": "UserController.java 内のクラスおよび公開メソッドに Javadoc を追記しました。"
    },
    {
      "guideline": "テストカバレッジの警告が発生しないよう、対応するテストクラスを必ず同行させること",
      "compliant": true,
      "evidence": "UserControllerTest.java に新規エンドポイントの結合テストを追加し、カバレッジを確保しました。"
    }
  ]
}
```
