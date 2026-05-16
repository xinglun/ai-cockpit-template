---
author: Ray
description: Rust stack adaptation example for AI Cockpit.
keywords:
  - rust
  - ai-cockpit
  - ai-agents
  - governance
---

# Rust Adaptation Example

Use this stack preset in `Makefile.ai.stack` for a Rust repository:

```make
PROJECT_FORMAT_CHECK = cargo fmt --all -- --check
PROJECT_TEST = cargo test
PROJECT_LINT = cargo clippy --all-targets -- -D warnings
```

Suggested guard patterns for `.ai/guards/coverage_policy.yaml`:

```yaml
production:
  include:
    - "src/**"
  exclude:
    - "tests/**"
    - "src/**/*test*.rs"

tests:
  include:
    - "tests/**"
    - "src/**/*test*.rs"
```

