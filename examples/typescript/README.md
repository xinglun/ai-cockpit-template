# TypeScript Adaptation Example

Use these Makefile targets in a TypeScript repository:

```make
project-format-check:
	npm run format:check

project-test:
	npm test

project-lint:
	npm run lint

quality: project-format-check project-test project-lint diff-check
```

Suggested guard patterns:

```yaml
production:
  include:
    - "src/**"
    - "app/**"
  exclude:
    - "**/*.test.ts"
    - "**/*.test.tsx"
    - "**/*.spec.ts"
    - "**/*.spec.tsx"

tests:
  include:
    - "**/*.test.ts"
    - "**/*.test.tsx"
    - "**/*.spec.ts"
    - "**/*.spec.tsx"
```

