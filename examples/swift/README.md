---
author: Ray
title: "Swift Adaptation Example"
description: Swift stack adaptation example for AI Cockpit.
keywords:
  - swift
  - ai-cockpit
  - ai-agents
  - governance
---

# Swift Adaptation Example

## 1. インストール

```sh
AI_COCKPIT_TEMPLATE_REF=v0.5.0 sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/v0.5.0/install.sh)" -- --stack swift --update-makefile
```

## 2. 品質ゲートとガード設定

Use this stack preset in `Makefile.ai.stack` for a Swift Package Manager repository:

```make
PROJECT_FORMAT_CHECK = swift format lint --recursive .
PROJECT_TEST = swift test
PROJECT_LINT = swift build -Xswiftc -warnings-as-errors
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "Sources/**"
  exclude:
    - "Tests/**"

tests:
  include:
    - "Tests/**"
```

---

## 3. 実践的な Swift 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な Swift 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_network_client",
  "mode": "code",
  "scope": [
    "Package.swift",
    "Sources/NetworkClient.swift",
    "Tests/NetworkClientTests.swift"
  ],
  "guidelines": [
    "非同期処理は可能な限り async/await を使用し、コールバック形式を避けること"
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
      "guideline": "非同期処理は可能な限り async/await を使用し、コールバック形式を避けること",
      "compliant": true,
      "evidence": "NetworkClient.swift の fetch メソッドを async throws 関数として実装しました。"
    }
  ]
}
```
