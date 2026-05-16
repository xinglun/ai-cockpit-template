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

