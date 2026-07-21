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

## 1. インストール

```sh
: "${AI_COCKPIT_TEMPLATE_REF:?set AI_COCKPIT_TEMPLATE_REF to the release tag}"
: "${AI_COCKPIT_TEMPLATE_RAW_BASE:?set AI_COCKPIT_TEMPLATE_RAW_BASE to the matching raw-content base}"
sh -c "$(curl -fsSL "${AI_COCKPIT_TEMPLATE_RAW_BASE}/${AI_COCKPIT_TEMPLATE_REF}/install.sh")" -- --stack typescript --update-makefile --create-adoption
```

## 2. 品質ゲート設定

TypeScript リポジトリでは、`Makefile.ai.stack` に次のスタックプリセットを設定します。

```make
PROJECT_FORMAT_CHECK = npm run format:check
PROJECT_TEST = npm test
PROJECT_LINT = npm run lint
```

## 3. Coverage Guard 設定

`.ai/guards/coverage_policy.yaml` には、次のガードパターンを推奨します。

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

## 4. Real TypeScript Web Fixture

`examples/fixtures/typescript-web` is a small executable local project. From that directory run:

```sh
npm install --ignore-scripts --no-audit --no-fund
npm run build
npm test
npm run lint
npm run format:check
npm run lifecycle
```

The lifecycle command records Install, Configure, Normal Work Item, Ambiguous Request, Critical Domain Change, Upgrade, Rollback, and Release Check. Ambiguous and critical-domain cases are blocked with resume conditions. External provider, identity, sandbox, immutable-audit, and enterprise-compliance evidence is intentionally `not_run`.

---

## 5. 実践的な TypeScript 用 Contract 設計例 (`*.contract.json` 抜粋)

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

## 5. guidelinesCompliance の記述例 (`*.summary.json` 抜粋)

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
