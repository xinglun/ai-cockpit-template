# Rust Adaptation Example

Use these Makefile targets in a Rust repository:

```make
project-format-check:
	cargo fmt --all -- --check

project-test:
	cargo test

project-lint:
	cargo clippy --all-targets -- -D warnings

quality: project-format-check project-test project-lint diff-check
```

Suggested guard patterns:

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

