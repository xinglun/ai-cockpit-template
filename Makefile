AI_CONTRACT ?= $(shell ls .ai/work-items/active/*.contract.json 2>/dev/null | head -n 1)
AI_SUMMARY ?= $(shell ls .ai/work-items/active/*.summary.json 2>/dev/null | head -n 1)
CONTRACT ?= $(AI_CONTRACT)
SUMMARY ?= $(AI_SUMMARY)
SUMMARY_ARGS ?= $(if $(CONTRACT),--contract $(CONTRACT))
STATUS_ARGS ?= $(if $(SUMMARY),--summary $(SUMMARY))
ARGS ?=
TASK ?=
TITLE ?=
MODE ?= investigate

.PHONY: help \
	project-format-check project-test project-lint diff-check quality \
	ai-start ai-finish check-ai check-ai-contract check-ai-work-item check-ai-scope check-ai-guards \
	check-ai-backtrack check-ai-coverage-guard check-ai-change-summary generate-cockpit-status check-ai-status \
	archive-work-item

help:
	@printf '%s\n' 'AI Cockpit template commands:'
	@printf '%s\n' '  make ai-start TASK=<task> TITLE="..." MODE=code'
	@printf '%s\n' '  make check-ai-contract CONTRACT=<contract.json>'
	@printf '%s\n' '  make check-ai-scope CONTRACT=<contract.json>'
	@printf '%s\n' '  make check-ai-guards'
	@printf '%s\n' '  make check-ai-backtrack'
	@printf '%s\n' '  make check-ai-coverage-guard'
	@printf '%s\n' '  make check-ai-change-summary SUMMARY=<summary.json> CONTRACT=<contract.json>'
	@printf '%s\n' '  make generate-cockpit-status CONTRACT=<contract.json> SUMMARY=<summary.json>'
	@printf '%s\n' '  make check-ai-status CONTRACT=<contract.json> SUMMARY=<summary.json>'
	@printf '%s\n' '  make ai-finish TASK=<task>'
	@printf '%s\n' '  make check-ai'
	@printf '%s\n' '  make quality'
	@printf '%s\n' '  make archive-work-item CONTRACT=<contract.json> [ARGS="--dry-run"]'
	@printf '%s\n' ''
	@printf '%s\n' 'Customize project-format-check, project-test, and project-lint for your stack.'

project-format-check:
	@printf '%s\n' 'No project formatter configured. Override project-format-check in this Makefile.'

project-test:
	@printf '%s\n' 'No project test command configured. Override project-test in this Makefile.'

project-lint:
	@printf '%s\n' 'No project linter configured. Override project-lint in this Makefile.'

diff-check:
	git diff --check

quality: project-format-check project-test project-lint diff-check

ai-start:
	python3 scripts/ai_start.py --task "$(TASK)" --title "$(TITLE)" --mode "$(MODE)"

check-ai-contract check-ai-work-item:
	python3 scripts/ai_check_work_item.py $(CONTRACT)

check-ai-scope:
	python3 scripts/ai_check_scope.py $(CONTRACT)

check-ai-guards:
	python3 scripts/ai_check_guards.py

check-ai-backtrack:
	python3 scripts/ai_check_backtrack.py

check-ai-coverage-guard:
	python3 scripts/ai_check_coverage_guard.py

check-ai-change-summary:
	python3 scripts/ai_check_summary.py $(SUMMARY) $(SUMMARY_ARGS) $(ARGS)

generate-cockpit-status:
	python3 scripts/ai_generate_status.py $(CONTRACT) $(STATUS_ARGS) $(ARGS)

check-ai-status:
	python3 scripts/ai_check_status.py .ai/cockpit/current_status.md $(SUMMARY_ARGS) $(STATUS_ARGS)

archive-work-item:
	python3 scripts/ai_archive_work_item.py $(CONTRACT) $(ARGS)

check-ai:
	@if [ -n "$(CONTRACT)" ]; then \
		"$${MAKE:-make}" check-ai-contract CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" check-ai-scope CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" check-ai-guards && \
		"$${MAKE:-make}" check-ai-backtrack && \
		"$${MAKE:-make}" check-ai-coverage-guard && \
		"$${MAKE:-make}" check-ai-change-summary SUMMARY="$(SUMMARY)" CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" generate-cockpit-status CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-status CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)"; \
	else \
		python3 scripts/ai_generate_status.py --no-active && \
		"$${MAKE:-make}" check-ai-guards && \
		"$${MAKE:-make}" check-ai-backtrack && \
		"$${MAKE:-make}" check-ai-coverage-guard; \
	fi

ai-finish:
	python3 scripts/ai_finish.py --task "$(TASK)"

