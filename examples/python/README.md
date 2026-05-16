---
author: Ray
description: Python stack adaptation example for AI Cockpit.
keywords:
  - python
  - ai-cockpit
  - ai-agents
  - governance
---

# Python Adaptation Example

Install with:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack python
```

Use this stack preset in `Makefile.ai.stack` for a Python repository:

```make
PROJECT_FORMAT_CHECK = python3 -m ruff format --check .
PROJECT_TEST = python3 -m pytest
PROJECT_LINT = python3 -m ruff check .
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "src/**"
    - "*.py"
  exclude:
    - "tests/**"
    - "test/**"
    - "**/*_test.py"
    - "**/test_*.py"

tests:
  include:
    - "tests/**"
    - "test/**"
    - "**/*_test.py"
    - "**/test_*.py"
```

