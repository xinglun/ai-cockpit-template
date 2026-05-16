---
author: Ray
title: "Kotlin Adaptation Example"
description: Kotlin stack adaptation example for AI Cockpit.
keywords:
  - kotlin
  - ai-cockpit
  - ai-agents
  - governance
---

# Kotlin Adaptation Example

Install with:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack kotlin
```

Use this stack preset in `Makefile.ai.stack` for a Gradle-based Kotlin repository:

```make
PROJECT_FORMAT_CHECK = ./gradlew spotlessCheck
PROJECT_TEST = ./gradlew test
PROJECT_LINT = ./gradlew check
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "src/main/kotlin/**"
  exclude:
    - "src/test/**"

tests:
  include:
    - "src/test/**"
```

