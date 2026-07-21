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
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
AI_PYTHON = PYTHONDONTWRITEBYTECODE=1 $(PYTHON)

.PHONY: help \
	test project-format-check project-test project-lint diff-check quality \
	ai-cockpit-project-format-check ai-cockpit-project-test ai-cockpit-project-lint ai-cockpit-diff-check ai-cockpit-quality \
	check-docs-metadata check-governance-complexity \
	check-ai-system-invariants check-ai-project-profile check-ai-guard-calibration cockpit-doctor cockpit-calibrate cockpit-validate-calibration \
	check-bandit-baseline check-sbom check-provenance check-release-evidence check-secret-scanning \
	check-release-distribution check-release-state-consistency \
	check-lockfile-reproducibility \
	check-trust-schemas check-trust-guards check-critical-domain-guards check-decision-protocol check-baseline-evidence \
	ai-start ai-finish ai-onboard check-ai check-ai-contract check-ai-work-item check-ai-scope check-ai-guards \
	ai-doctor check-ai-adoption-ready \
	check-ai-agent-risk ai-checkpoint check-ai-backtrack check-ai-coverage-guard check-ai-guidelines check-ai-review-policy template-adoption-ready \
	check-ai-scenario-coverage check-ai-start-receipt generate-ai-preflight-review check-ai-preflight-review ai-preflight \
	check-ai-change-summary generate-cockpit-status check-ai-status check-ai-status-consistency repair-ai-status archive-work-item ai-close-work-item check-ai-pr check-ai-diff-ownership ai-pre-merge

check-ai-diff-ownership:
	$(AI_PYTHON) scripts/ai_check_diff_ownership.py $(if $(AI_BASE_COMMIT),--base $(AI_BASE_COMMIT),) $(if $(CONTRACT),--contract $(CONTRACT),)

check-ai-start-receipt:
	$(AI_PYTHON) scripts/ai_start_receipt.py --contract "$(CONTRACT)" $(if $(RECEIPT),--receipt "$(RECEIPT)",)

ai-pre-merge:
	@set -e; \
		echo 'Content quality:'; env -u AI_BASE_COMMIT -u AI_COCKPIT_EXECUTION_MODE -u MAKEFLAGS -u MAKEOVERRIDES $(shell command -v make) quality || { echo 'ALLOW COMMIT / MERGE: no (content quality failed)'; exit 1; }; \
		echo 'Lifecycle evidence:'; env -u AI_BASE_COMMIT -u AI_COCKPIT_EXECUTION_MODE -u MAKEFLAGS -u MAKEOVERRIDES $(shell command -v make) check-ai-status-consistency || { echo 'ALLOW COMMIT / MERGE: no (lifecycle evidence failed)'; exit 1; }; \
		echo 'Diff ownership preview:'; $(shell command -v make) check-ai-diff-ownership AI_BASE_COMMIT="$(AI_BASE_COMMIT)" || { echo 'ALLOW COMMIT / MERGE: no (diff ownership failed)'; exit 1; }; \
		echo 'PR ownership:'; $(shell command -v make) check-ai-pr AI_BASE_COMMIT="$(AI_BASE_COMMIT)" || { echo 'ALLOW COMMIT / MERGE: no (PR ownership failed)'; exit 1; }; \
		echo 'ALLOW COMMIT / MERGE: yes'

help:
	@printf '%s\n' 'AI Cockpit template commands:'
	@printf '%s\n' '  make ai-start TASK=<task> TITLE="..." MODE=code'
	@printf '%s\n' '  make ai-onboard [PHASE=1|2|3]'
	@printf '%s\n' '  make ai-doctor'
	@printf '%s\n' '  make check-ai-adoption-ready'
	@printf '%s\n' '  make template-adoption-ready  # explicit template-maintenance readiness mode'
	@printf '%s\n' '  make check-ai-contract CONTRACT=<contract.json>'
	@printf '%s\n' '  make check-ai-scope CONTRACT=<contract.json>'
	@printf '%s\n' '  make check-ai-guards'
	@printf '%s\n' '  make check-ai-agent-risk CONTRACT=<contract.json> SUMMARY=<summary.json>'
	@printf '%s\n' '  make ai-checkpoint CONTRACT=<contract.json> SUMMARY=<summary.json> STAGE=before_finish'
	@printf '%s\n' '  make check-ai-review-policy SUMMARY=<summary.json>'
	@printf '%s\n' '  make check-ai-backtrack'
	@printf '%s\n' '  make check-ai-coverage-guard'
	@printf '%s\n' '  make check-ai-scenario-coverage'
	@printf '%s\n' '  make ai-preflight'
	@printf '%s\n' '  make generate-ai-preflight-review'
	@printf '%s\n' '  make check-ai-preflight-review'
	@printf '%s\n' '  make check-ai-change-summary SUMMARY=<summary.json> CONTRACT=<contract.json>'
	@printf '%s\n' '  make generate-cockpit-status CONTRACT=<contract.json> SUMMARY=<summary.json>'
	@printf '%s\n' '  make check-ai-status CONTRACT=<contract.json> SUMMARY=<summary.json>'
	@printf '%s\n' '  make check-ai-status-consistency'
	@printf '%s\n' '  make repair-ai-status'
	@printf '%s\n' '  make ai-finish TASK=<task>'
	@printf '%s\n' '  make check-ai'
	@printf '%s\n' '  make quality'
	@printf '%s\n' '  make test'
	@printf '%s\n' '  make check-docs-metadata'
	@printf '%s\n' '  make check-governance-complexity'
	@printf '%s\n' '  make check-ai-system-invariants'
	@printf '%s\n' '  make cockpit-doctor'
	@printf '%s\n' '  make cockpit-calibrate'
	@printf '%s\n' '  make cockpit-validate-calibration'
	@printf '%s\n' '  make check-release-distribution  # networked public release contract'
	@printf '%s\n' '  make check-trust-schemas'
	@printf '%s\n' '  make check-trust-guards'
	@printf '%s\n' '  make check-decision-protocol'
	@printf '%s\n' '  make archive-work-item CONTRACT=<contract.json> [ARGS="--dry-run"]'
	@printf '%s\n' '  make ai-close-work-item TASK=<task>  # verify merge, synchronize base, and clean branches'
	@printf '%s\n' ''
	@printf '%s\n' 'Customize project-format-check, project-test, and project-lint for your stack.'

project-format-check:
	$(AI_PYTHON) -m ruff format --check scripts tests
	git diff --check

project-test:
	$(AI_PYTHON) -m pytest -q --cov=scripts --cov-report=term-missing --cov-report=json:target/coverage.json --cov-fail-under=85
	$(AI_PYTHON) scripts/check_critical_coverage.py

test: project-test unsupported-claim-regression

unsupported-claim-regression:
	$(AI_PYTHON) scripts/unsupported_claim_gate.py

project-lint:
	$(AI_PYTHON) -m ruff check scripts tests
	$(AI_PYTHON) -m mypy scripts/*.py
	$(AI_PYTHON) -m bandit -q -r scripts -ll
	$(AI_PYTHON) scripts/check_bandit_baseline.py
	$(AI_PYTHON) scripts/check_governance_complexity.py
	$(AI_PYTHON) scripts/check_supply_chain.py secrets
	$(AI_PYTHON) -m py_compile scripts/*.py tests/*.py

diff-check:
	git diff --check

check-docs-metadata:
	$(AI_PYTHON) scripts/check_docs_metadata.py

check-governance-complexity:
	$(AI_PYTHON) scripts/check_governance_complexity.py

check-release-distribution:
	$(AI_PYTHON) scripts/check_release_distribution.py

check-release-state-consistency:
	$(AI_PYTHON) scripts/check_release_state_consistency.py --root .

check-trust-schemas:
	$(AI_PYTHON) scripts/ai_trust_schema.py --check

check-trust-guards:
	$(AI_PYTHON) -m pytest -q tests/test_trust_guards.py

check-critical-domain-guards:
	$(AI_PYTHON) -m pytest -q tests/test_critical_domain_guards.py

check-baseline-evidence:
	$(AI_PYTHON) -m pytest -q tests/test_baseline_evidence.py

check-decision-protocol:
	$(AI_PYTHON) -m pytest -q tests/test_decision_protocol.py

check-ai-system-invariants:
	$(AI_PYTHON) scripts/check_system_invariants.py

check-bandit-baseline:
	$(AI_PYTHON) scripts/check_bandit_baseline.py

check-sbom:
	$(AI_PYTHON) scripts/check_supply_chain.py sbom

check-provenance:
	$(AI_PYTHON) scripts/check_supply_chain.py provenance

check-release-evidence:
	$(AI_PYTHON) scripts/check_supply_chain.py release

check-lockfile-reproducibility:
	@tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; cp requirements-dev.lock "$$tmp/"; (cd "$$tmp" && ln -s "$(CURDIR)/requirements-dev.in" requirements-dev.in && "$(abspath $(PYTHON))" -m piptools compile --no-upgrade --generate-hashes --allow-unsafe --output-file=requirements-dev.lock requirements-dev.in >/dev/null && sed -i.bak -E 's/^# This file is autogenerated by pip-compile with Python .*/# This file is autogenerated by pip-compile with canonical Python 3.10/' requirements-dev.lock && rm requirements-dev.lock.bak); cmp -s "$$tmp/requirements-dev.lock" requirements-dev.lock || { echo 'lockfile reproducibility check failed: regenerated requirements-dev.lock differs from the committed lockfile' >&2; exit 1; }

check-secret-scanning:
	$(AI_PYTHON) scripts/check_supply_chain.py secrets

check-dependency-vulnerabilities:
	$(AI_PYTHON) scripts/check_supply_chain.py vulnerabilities

cockpit-doctor:
	$(AI_PYTHON) scripts/ai_doctor.py --root .
	$(AI_PYTHON) scripts/ai_project_doctor.py --root .

cockpit-calibrate:
	$(AI_PYTHON) scripts/ai_calibrate.py generate --root .

cockpit-validate-calibration:
	$(AI_PYTHON) scripts/ai_calibrate.py validate --profile "$(or $(PROFILE),.ai/project_profile.proposed.yaml)" $(ARGS)

check-ai-project-profile:
	$(AI_PYTHON) scripts/ai_calibrate.py validate --profile .ai/project_profile.yaml --confirmed

check-ai-guard-calibration: check-ai-project-profile
	$(AI_PYTHON) scripts/ai_check_guard_calibration.py --root .

quality: project-format-check project-test unsupported-claim-regression project-lint diff-check check-docs-metadata check-ai-system-invariants check-ai-project-profile check-ai-guard-calibration check-ai-status-consistency check-bandit-baseline check-sbom check-provenance check-release-evidence check-secret-scanning check-dependency-vulnerabilities check-trust-schemas check-trust-guards check-critical-domain-guards check-decision-protocol check-baseline-evidence

ai-cockpit-project-format-check: project-format-check

ai-cockpit-project-test: project-test

ai-cockpit-project-lint: project-lint

ai-cockpit-diff-check: diff-check

ai-cockpit-quality: quality

ai-start:
	$(AI_PYTHON) scripts/ai_start.py --task "$(TASK)" --title "$(TITLE)" --mode "$(MODE)"

ai-onboard:
	$(AI_PYTHON) scripts/ai_onboard.py --root . $(if $(PHASE),--phase $(PHASE),) $(if $(SKIP_CALIBRATE),--skip-calibrate,) $(if $(SKIP_READINESS_CHECKS),--skip-readiness-checks,)

ai-doctor:
	$(AI_PYTHON) scripts/ai_doctor.py --root .

check-ai-adoption-ready:
	$(AI_PYTHON) scripts/ai_check_adoption_ready.py --root .

template-adoption-ready:
	AI_COCKPIT_EXECUTION_MODE=template_maintenance $(shell command -v make) check-ai-adoption-ready

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

check-ai-scenario-coverage:
	$(AI_PYTHON) scripts/ai_check_scenario_coverage.py $(if $(CONTRACT),--contract $(CONTRACT)) $(if $(SUMMARY),--summary $(SUMMARY))

ai-preflight:
	$(AI_PYTHON) scripts/ai_preflight_review.py $(if $(CONTRACT),--contract $(CONTRACT))
	$(AI_PYTHON) scripts/ai_preflight_review.py --check $(if $(CONTRACT),--contract $(CONTRACT))

generate-ai-preflight-review:
	$(AI_PYTHON) scripts/ai_preflight_review.py $(if $(CONTRACT),--contract $(CONTRACT))

check-ai-preflight-review:
	$(AI_PYTHON) scripts/ai_preflight_review.py --check $(if $(CONTRACT),--contract $(CONTRACT))

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

ai-close-work-item:
	$(AI_PYTHON) scripts/ai_close_work_item.py --task "$(TASK)"

check-ai:
	@if [ -n "$(CONTRACT)" ]; then \
		"$${MAKE:-make}" check-ai-contract CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" check-ai-scope CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" check-ai-guards CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" check-ai-agent-risk CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-review-policy SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-backtrack && \
		"$${MAKE:-make}" check-ai-coverage-guard && \
		"$${MAKE:-make}" check-ai-scenario-coverage CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-guidelines CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-change-summary SUMMARY="$(SUMMARY)" CONTRACT="$(CONTRACT)" && \
		"$${MAKE:-make}" generate-cockpit-status CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-status CONTRACT="$(CONTRACT)" SUMMARY="$(SUMMARY)" && \
		"$${MAKE:-make}" check-ai-status-consistency; \
	else \
		"$${MAKE:-make}" check-ai-status-consistency && \
		"$${MAKE:-make}" check-ai-backtrack && \
		"$${MAKE:-make}" check-ai-coverage-guard && \
		"$${MAKE:-make}" check-ai-diff-ownership && \
		test -n "$(AI_BASE_COMMIT)" && \
		"$${MAKE:-make}" check-ai-pr AI_BASE_COMMIT="$(AI_BASE_COMMIT)"; \
	fi

check-ai-pr:
	$(AI_PYTHON) scripts/ai_check_pr.py --base "$(AI_BASE_COMMIT)"

ai-finish:
	$(AI_PYTHON) scripts/ai_finish.py --task "$(TASK)"
