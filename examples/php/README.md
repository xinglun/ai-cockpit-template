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
AI_COCKPIT_TEMPLATE_REF=v0.5.9 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.9/install.sh)" -- --stack php --update-makefile --create-adoption
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
