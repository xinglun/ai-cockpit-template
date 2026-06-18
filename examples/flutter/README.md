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

Use this stack preset in `Makefile.ai.stack` for a Flutter repository:

```make
PROJECT_FORMAT_CHECK = dart format --set-exit-if-changed .
PROJECT_TEST = flutter test
PROJECT_LINT = flutter analyze
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

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

## 3. 実践的な Flutter/Dart 用 Contract 設計例 (`*.contract.json` 抜粋)

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

## 4. guidelinesCompliance の記述例 (`*.summary.json` 抜粋)

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
