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
PYTHON ?= python3
AI_PYTHON ?= PYTHONDONTWRITEBYTECODE=1 $(PYTHON)

.PHONY: help \
	project-format-check project-test project-lint diff-check quality \
	ai-start ai-finish check-ai check-ai-contract check-ai-work-item check-ai-scope check-ai-guards \
	check-ai-agent-risk ai-checkpoint check-ai-backtrack check-ai-coverage-guard check-ai-guidelines check-ai-review-policy \
	check-ai-change-summary generate-cockpit-status check-ai-status check-ai-status-consistency repair-ai-status archive-work-item check-ai-pr

help:
	@printf '%s\n' 'AI Cockpit template commands:'
	@printf '%s\n' '  make ai-start TASK=<task> TITLE="..." MODE=code'
	@printf '%s\n' '  make check-ai-contract CONTRACT=<contract.json>'
	@printf '%s\n' '  make check-ai-scope CONTRACT=<contract.json>'
	@printf '%s\n' '  make check-ai-guards'
	@printf '%s\n' '  make check-ai-agent-risk CONTRACT=<contract.json> SUMMARY=<summary.json>'
	@printf '%s\n' '  make ai-checkpoint CONTRACT=<contract.json> SUMMARY=<summary.json> STAGE=before_finish'
	@printf '%s\n' '  make check-ai-review-policy SUMMARY=<summary.json>'
	@printf '%s\n' '  make check-ai-backtrack'
	@printf '%s\n' '  make check-ai-coverage-guard'
	@printf '%s\n' '  make check-ai-change-summary SUMMARY=<summary.json> CONTRACT=<contract.json>'
	@printf '%s\n' '  make generate-cockpit-status CONTRACT=<contract.json> SUMMARY=<summary.json>'
	@printf '%s\n' '  make check-ai-status CONTRACT=<contract.json> SUMMARY=<summary.json>'
	@printf '%s\n' '  make check-ai-status-consistency'
	@printf '%s\n' '  make repair-ai-status'
	@printf '%s\n' '  make ai-finish TASK=<task>'
	@printf '%s\n' '  make check-ai'
	@printf '%s\n' '  make quality'
	@printf '%s\n' '  make archive-work-item CONTRACT=<contract.json> [ARGS="--dry-run"]'
	@printf '%s\n' ''
	@printf '%s\n' 'Customize project-format-check, project-test, and project-lint for your stack.'

project-format-check:
	git diff --check

project-test:
	$(AI_PYTHON) -m pytest -q

project-lint:
	$(AI_PYTHON) -m py_compile scripts/*.py tests/*.py

diff-check:
	git diff --check

quality: project-format-check project-test project-lint diff-check

ai-start:
	$(AI_PYTHON) scripts/ai_start.py --task "$(TASK)" --title "$(TITLE)" --mode "$(MODE)"

check-ai-contract check-ai-work-item:
	$(AI_PYTHON) scripts/ai_check_work_item.py $(CONTRACT)

check-ai-scope:
	$(AI_PYTHON) scripts/ai_check_scope.py $(CONTRACT)

check-ai-guards:
	$(AI_PYTHON) scripts/ai_check_guards.py $(if $(CONTRACT),--contract $(CONTRACT))

check-ai-agent-risk:
	$(AI_PYTHON) scripts/ai_check_agent_risk.py $(if $(CONTRACT),--contract $(CONTRACT)) $(if $(SUMMARY),--summary $(SUMMARY))

ai-checkpoint:
	$(AI_PYTHON) scripts/ai_checkpoint.py --contract $(CONTRACT) $(if $(SUMMARY),--summary $(SUMMARY)) --stage "$(or $(STAGE),manual)"

check-ai-backtrack:
	$(AI_PYTHON) scripts/ai_check_backtrack.py

check-ai-coverage-guard:
	$(AI_PYTHON) scripts/ai_check_coverage_guard.py

check-ai-guidelines:
	$(AI_PYTHON) scripts/ai_check_guidelines.py --contract $(CONTRACT) --summary $(SUMMARY)

check-ai-review-policy:
	$(AI_PYTHON) scripts/ai_check_review_policy.py $(if $(SUMMARY),--summary $(SUMMARY))

check-ai-change-summary:
	$(AI_PYTHON) scripts/ai_check_summary.py $(SUMMARY) $(SUMMARY_ARGS) $(ARGS)

generate-cockpit-status:
	$(AI_PYTHON) scripts/ai_generate_status.py $(CONTRACT) $(STATUS_ARGS) $(ARGS)

check-ai-status:
	$(AI_PYTHON) scripts/ai_check_status.py .ai/cockpit/current_status.md $(SUMMARY_ARGS) $(STATUS_ARGS)

check-ai-status-consistency:
	$(AI_PYTHON) scripts/ai_check_status_consistency.py

repair-ai-status:
	$(AI_PYTHON) scripts/ai_check_status_consistency.py --repair

archive-work-item:
	$(AI_PYTHON) scripts/ai_archive_work_item.py $(CONTRACT) $(ARGS)

check-ai:
	@if [ -n "$(CONTRACT)" ]; then \
		"$${MAKE:-make}" check-ai-contract CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" check-ai-scope CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" check-ai-guards CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" check-ai-agent-risk CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-review-policy SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-backtrack && \
		"$${MAKE:-make}" check-ai-coverage-guard && \
		"$${MAKE:-make}" check-ai-guidelines CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-change-summary SUMMARY="$(SUMMARY)" CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" generate-cockpit-status CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-status CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-status-consistency; \
	else \
		$(AI_PYTHON) scripts/ai_generate_status.py --no-active && \
		"$${MAKE:-make}" check-ai-status-consistency && \
		"$${MAKE:-make}" check-ai-guards && \
		"$${MAKE:-make}" check-ai-agent-risk && \
		"$${MAKE:-make}" check-ai-review-policy && \
		"$${MAKE:-make}" check-ai-backtrack && \
		"$${MAKE:-make}" check-ai-coverage-guard; \
	fi

check-ai-pr:
	$(AI_PYTHON) scripts/ai_check_pr.py --base "$(AI_BASE_COMMIT)"

ai-finish:
	$(AI_PYTHON) scripts/ai_finish.py --task "$(TASK)"
