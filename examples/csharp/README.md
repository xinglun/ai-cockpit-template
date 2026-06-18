---
author: Ray
title: "C# Adaptation Example"
description: C# stack adaptation example for AI Cockpit.
keywords:
  - csharp
  - dotnet
  - ai-cockpit
  - ai-agents
  - governance
---

# C# Adaptation Example

Install with:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack csharp
```

Use this stack preset in `Makefile.ai.stack` for a .NET repository:

```make
PROJECT_FORMAT_CHECK = dotnet format --verify-no-changes
PROJECT_TEST = dotnet test
PROJECT_LINT = dotnet build -warnaserror
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "src/**"
  exclude:
    - "tests/**"
    - "**/*Tests/**"

tests:
  include:
    - "tests/**"
    - "**/*Tests/**"
```

---

## 3. 実践的な C# 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な C# (.NET) 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_billing_service",
  "mode": "code",
  "scope": [
    "src/BillingService/BillingService.csproj",
    "src/BillingService/Services/PaymentProcessor.cs",
    "tests/BillingService.Tests/PaymentProcessorTests.cs"
  ],
  "guidelines": [
    "すべてのパブリックメソッドおよびインターフェースに XML ドキュメントコメントを記述すること"
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
      "guideline": "すべてのパブリックメソッドおよびインターフェースに XML ドキュメントコメントを記述すること",
      "compliant": true,
      "evidence": "PaymentProcessor.cs 内の公開インターフェースおよびメソッドにトリプルスラッシュ (///) による XML ドキュメントを記述しました。"
    }
  ]
}
```
