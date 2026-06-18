---
author: Ray
title: "TypeScript Adaptation Example"
description: TypeScript stack adaptation example for AI Cockpit.
keywords:
  - typescript
  - ai-cockpit
  - ai-agents
  - governance
---

# TypeScript Adaptation Example

Use this stack preset in `Makefile.ai.stack` for a TypeScript repository:

```make
PROJECT_FORMAT_CHECK = npm run format:check
PROJECT_TEST = npm test
PROJECT_LINT = npm run lint
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "src/**"
    - "app/**"
  exclude:
    - "**/*.test.ts"
    - "**/*.test.tsx"
    - "**/*.spec.ts"
    - "**/*.spec.tsx"

tests:
  include:
    - "**/*.test.ts"
    - "**/*.test.tsx"
    - "**/*.spec.ts"
    - "**/*.spec.tsx"
```

---

## 3. 実践的な TypeScript 用 Contract 設計例 (`*.contract.json` 抜粋)

以下は、典型的な TypeScript 機能追加時の Contract 設定例です。

```json
{
  "contractVersion": 2,
  "workItemId": "add_api_endpoint",
  "mode": "code",
  "scope": [
    "package.json",
    "src/routes/api.ts",
    "src/routes/__tests__/api.test.ts"
  ],
  "guidelines": [
    "すべての新 API には JSDoc を記述すること",
    "型定義は any を極力避け、厳格に定義すること"
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
      "guideline": "すべての新 API には JSDoc を記述すること",
      "compliant": true,
      "evidence": "src/routes/api.ts のエンドポイント関数に JSDoc コメントを追加しました。"
    },
    {
      "guideline": "型定義は any を極力避け、厳格に定義すること",
      "compliant": true,
      "evidence": "追加したインターフェースおよび変数定義において any タイプは使用していません。"
    }
  ]
}
```
