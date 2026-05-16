---
author: Ray
description: Ruby stack adaptation example for AI Cockpit.
keywords:
  - ruby
  - ai-cockpit
  - ai-agents
  - governance
---

# Ruby Adaptation Example

Install with:

```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack ruby
```

Use this stack preset in `Makefile.ai.stack` for a Ruby repository:

```make
PROJECT_FORMAT_CHECK = bundle exec rubocop --format simple
PROJECT_TEST = bundle exec rake test
PROJECT_LINT = bundle exec rubocop
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "app/**"
    - "lib/**"
  exclude:
    - "test/**"
    - "spec/**"

tests:
  include:
    - "test/**"
    - "spec/**"
```

