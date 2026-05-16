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

Install with:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack swift
```

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

