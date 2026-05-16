---
author: Ray
title: "Java Adaptation Example"
description: Java stack adaptation example for AI Cockpit.
keywords:
  - java
  - ai-cockpit
  - ai-agents
  - governance
---

# Java Adaptation Example

Install with:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack java
```

Use this stack preset in `Makefile.ai.stack` for a Gradle-based Java repository:

```make
PROJECT_FORMAT_CHECK = ./gradlew spotlessCheck
PROJECT_TEST = ./gradlew test
PROJECT_LINT = ./gradlew check
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "src/main/java/**"
  exclude:
    - "src/test/**"

tests:
  include:
    - "src/test/**"
```

