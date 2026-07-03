---
author: Ray
title: "Python Adaptation Example"
description: Python stack adaptation example for AI Cockpit.
keywords:
  - python
  - ai-cockpit
  - ai-agents
  - governance
---

# Python Adaptation Example

## 1. インストール

```sh
AI_COCKPIT_TEMPLATE_REF=v0.5.16 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.16/install.sh)" -- --stack python --update-makefile --create-adoption
```

## 2. 品質ゲートとガード設定

Python リポジトリでは、`Makefile.ai.stack` に次のスタックプリセットを設定します。

```make
PROJECT_FORMAT_CHECK = $(PYTHON) -m ruff format --check .
PROJECT_TEST = $(PYTHON) -m pytest
PROJECT_LINT = $(PYTHON) -m ruff check .
```

`.ai/guards/coverage_policy.yaml` には、次のガードパターンを推奨します。

```yaml
production:
  include:
    - "src/**"
    - "*.py"
  exclude:
    - "tests/**"
    - "test/**"
    - "**/*_test.py"
    - "**/test_*.py"

tests:
  include:
    - "tests/**"
    - "test/**"
    - "**/*_test.py"
    - "**/test_*.py"
```

---

## 3. 実践的な Python 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な Python 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_user_auth",
  "mode": "code",
  "scope": [
    "requirements.txt",
    "src/auth.py",
    "tests/test_auth.py"
  ],
  "guidelines": [
    "すべての新関数には docstring (Google Style) を記述すること",
    "外部ライブラリを追加する場合は requirements.txt にピン留めすること"
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
      "guideline": "すべての新関数には docstring (Google Style) を記述すること",
      "compliant": true,
      "evidence": "src/auth.py 内のすべての追加関数に PEP 257 準拠の docstring を追記しました。"
    },
    {
      "guideline": "外部ライブラリを追加する場合は requirements.txt にピン留めすること",
      "compliant": true,
      "evidence": "追加パッケージは存在しないため、requirements.txt の更新はありません。"
    }
  ]
}
```
