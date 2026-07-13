---
author: Ray
title: "PHP Adaptation Example"
description: PHP stack adaptation example for AI Cockpit.
keywords:
  - php
  - ai-cockpit
  - ai-agents
  - governance
---

# PHP Adaptation Example

## 1. インストール

```sh
: "${AI_COCKPIT_TEMPLATE_REF:?set AI_COCKPIT_TEMPLATE_REF to the release tag}"
: "${AI_COCKPIT_TEMPLATE_RAW_BASE:?set AI_COCKPIT_TEMPLATE_RAW_BASE to the matching raw-content base}"
sh -c "$(curl -fsSL "${AI_COCKPIT_TEMPLATE_RAW_BASE}/${AI_COCKPIT_TEMPLATE_REF}/install.sh")" -- --stack php --update-makefile --create-adoption
```

## 2. 品質ゲートとガード設定

PHP リポジトリでは、`Makefile.ai.stack` に次のスタックプリセットを設定します。

```make
PROJECT_FORMAT_CHECK = vendor/bin/php-cs-fixer fix --dry-run --diff
PROJECT_TEST = vendor/bin/phpunit
PROJECT_LINT = vendor/bin/phpstan analyse
```

`.ai/guards/coverage_policy.yaml` には、次のガードパターンを推奨します。

```yaml
production:
  include:
    - "src/**"
    - "app/**"
  exclude:
    - "tests/**"

tests:
  include:
    - "tests/**"
```

---

## 3. 実践的な PHP 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な PHP 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_user_repository",
  "mode": "code",
  "scope": [
    "composer.json",
    "src/Repository/UserRepository.php",
    "tests/Repository/UserRepositoryTest.php"
  ],
  "guidelines": [
    "すべての新規メソッドには PHPDoc タイプヒントを記述すること",
    "PHPStan の静的解析でエラーが発生しないこと"
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
      "guideline": "すべての新規メソッドには PHPDoc タイプヒントを記述すること",
      "compliant": true,
      "evidence": "UserRepository.php 内のすべてのパブリックメソッドに適切な PHPDoc コメントを追加しました。"
    },
    {
      "guideline": "PHPStan の静的解析でエラーが発生しないこと",
      "compliant": true,
      "evidence": "vendor/bin/phpstan を実行し、変更対象コードに警告がないことを確認しました。"
    }
  ]
}
```
