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

