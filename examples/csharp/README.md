---
author: Ray
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

