---
author: Ray
title: "Go Adaptation Example"
description: Go stack adaptation example for AI Cockpit.
keywords:
  - go
  - ai-cockpit
  - ai-agents
  - governance
---

# Go Adaptation Example

Install with:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack go
```

Use this stack preset in `Makefile.ai.stack` for a Go repository:

```make
PROJECT_FORMAT_CHECK = test -z "$$(gofmt -l .)"
PROJECT_TEST = go test ./...
PROJECT_LINT = go vet ./...
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "**/*.go"
  exclude:
    - "**/*_test.go"

tests:
  include:
    - "**/*_test.go"
```

