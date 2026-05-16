---
author: Ray
title: "PHP Adaptation Example"
description: PHP stack adaptation example for AI Cockpit.
keywords:
  - php
  - ai-cockpit
  - ai-agents
  - governance
---

# PHP Adaptation Example

Install with:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack php
```

Use this stack preset in `Makefile.ai.stack` for a PHP repository:

```make
PROJECT_FORMAT_CHECK = vendor/bin/php-cs-fixer fix --dry-run --diff
PROJECT_TEST = vendor/bin/phpunit
PROJECT_LINT = vendor/bin/phpstan analyse
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "src/**"
    - "app/**"
  exclude:
    - "tests/**"

tests:
  include:
    - "tests/**"
```

