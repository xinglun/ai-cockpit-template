# Go stack preset for AI Cockpit.
# Coverage policy: Go uses *_test.go convention (inline tests).
# See examples/go/README.md for coverage_policy.yaml patterns.

PROJECT_FORMAT_CHECK = test -z "$$(gofmt -l .)"
PROJECT_TEST = go test ./...
PROJECT_LINT = go vet ./...
