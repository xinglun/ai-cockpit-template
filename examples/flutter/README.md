---
author: Ray
title: "Flutter Adaptation Example"
description: Flutter stack adaptation example for AI Cockpit.
keywords:
  - flutter
  - dart
  - ai-cockpit
  - ai-agents
  - governance
---

# Flutter Adaptation Example

## 1. インストール

```sh
AI_COCKPIT_TEMPLATE_REF=v0.5.3 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.3/install.sh)" -- --stack flutter --update-makefile --create-adoption
```

## 2. 品質ゲート設定

Flutter リポジトリでは、`Makefile.ai.stack` に次のスタックプリセットを設定します。

```make
PROJECT_FORMAT_CHECK = dart format --set-exit-if-changed .
PROJECT_TEST = flutter test
PROJECT_LINT = flutter analyze
```

## 3. Coverage Guard 設定

`.ai/guards/coverage_policy.yaml` には、次のガードパターンを推奨します。

```yaml
production:
  include:
    - "lib/**"
  exclude:
    - "test/**"
    - "**/*_test.dart"

tests:
  include:
    - "test/**"
    - "**/*_test.dart"
```

---

## 4. 実践的な Flutter/Dart 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な Flutter 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_login_button",
  "mode": "code",
  "scope": [
    "pubspec.yaml",
    "lib/widgets/login_button.dart",
    "test/widgets/login_button_test.dart"
  ],
  "guidelines": [
    "状態管理ロジックは UI Widget 内に記述せず、ViewModel または BLoC に分離すること",
    "新規 Widget に対するウィジェットテストを必ず追加すること"
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

## 5. guidelinesCompliance の記述例 (`*.summary.json` 抜粋)

上記ガイドラインに適合したことを証明する要約（Summary）の記述例です。

```json
{
  "guidelinesCompliance": [
    {
      "guideline": "状態管理ロジックは UI Widget 内に記述せず、ViewModel または BLoC に分離すること",
      "compliant": true,
      "evidence": "ボタンのタップ処理ロジックを LoginViewModel に委譲し、Widget 自体はステートレスに保ちました。"
    },
    {
      "guideline": "新規 Widget に対するウィジェットテストを必ず追加すること",
      "compliant": true,
      "evidence": "test/widgets/login_button_test.dart を新規作成し、タップイベントの検証を追加しました。"
    }
  ]
}
```
