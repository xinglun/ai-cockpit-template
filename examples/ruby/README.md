---
author: Ray
title: "Ruby Adaptation Example"
description: Ruby stack adaptation example for AI Cockpit.
keywords:
  - ruby
  - ai-cockpit
  - ai-agents
  - governance
---

# Ruby Adaptation Example

Install with:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack ruby
```

Use this stack preset in `Makefile.ai.stack` for a Ruby repository:

```make
PROJECT_FORMAT_CHECK = bundle exec rubocop --format simple
PROJECT_TEST = bundle exec rake test
PROJECT_LINT = bundle exec rubocop
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "app/**"
    - "lib/**"
  exclude:
    - "test/**"
    - "spec/**"

tests:
  include:
    - "test/**"
    - "spec/**"
```

---

## 3. 実践的な Ruby 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な Ruby (Rails) 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_user_model",
  "mode": "code",
  "scope": [
    "Gemfile",
    "app/models/user.rb",
    "spec/models/user_spec.rb"
  ],
  "guidelines": [
    "新機能に対応するモデルスペック (RSpec) を必ず追加すること",
    "RuboCop の警告が発生しない綺麗なコードを書くこと"
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
      "guideline": "新機能に対応するモデルスペック (RSpec) を必ず追加すること",
      "compliant": true,
      "evidence": "spec/models/user_spec.rb に新しいバリデーションとアソシエーションのテストを追記しました。"
    },
    {
      "guideline": "RuboCop の警告が発生しない綺麗なコードを書くこと",
      "compliant": true,
      "evidence": "bundle exec rubocop を実行し、追加ファイルに警告がないことを確認しました。"
    }
  ]
}
```
