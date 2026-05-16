# Flutter Adaptation Example

Use these Makefile targets in a Flutter repository:

```make
project-format-check:
	dart format --set-exit-if-changed .

project-test:
	flutter test

project-lint:
	flutter analyze

quality: project-format-check project-test project-lint diff-check
```

Suggested guard patterns:

```yaml
production:
  include:
    - "lib/**"
  exclude:
    - "test/**"
    - "**/*_test.dart"

tests:
  include:
    - "test/**"
    - "**/*_test.dart"
```

