#!/usr/bin/env bash
set -euo pipefail

plan="docs/superpowers/plans/2026-07-22-conditional-go-review-remediation.md"
index="docs/superpowers/plans/README.md"
test -f "$plan"
test -f "$index"
rg -q '^\*\*Status:\*\* historical' "$plan"
rg -q 'cleanup Work Item' "$plan"
for marker in '#242' '#244' '#246' '#247' '#248' '#249' '#251' '#252' '#253' '#254'; do
  rg -q "$marker" "$plan"
done
for archive in \
  conditional_go_review_execution_plan \
  conditional_go_capability_truth_matrix \
  conditional_go_installed_runtime_parity \
  conditional_go_verified_quick_install \
  conditional_go_calibration_scaffold_core \
  conditional_go_calibration_inventory_status_matrix \
  conditional_go_bootstrap_lifecycle_schema \
  conditional_go_ownership_installed_lifecycle \
  conditional_go_ci_release_evidence \
  conditional_go_complexity_installer; do
  test -f ".ai/work-items/archive/2026/${archive}.archive-manifest.json"
  rg -q "$archive" "$plan"
done
rg -q '已完成/需审计' "$index"
rg -q '已替代/错误计划' "$index"
rg -q '引用扫描并记录替代证据后删除' "$index"
for entry in \
  'docs/superpowers/plans/2026-07-22-project-calibration-recalibration.md:project-calibration-final-plan-reconciliation' \
  'docs/superpowers/plans/2026-07-22-installed-lifecycle-review-remediation.md:installed-lifecycle-plan-cleanup' \
  'docs/superpowers/plans/2026-07-22-ai-cockpit-governance-hardening.md:ai-cockpit-governance-hardening'; do
  plan_path=${entry%%:*}
  work_item=${entry#*:}
  for evidence in contract summary archive-manifest; do
    evidence_path=".ai/work-items/archive/2026/${work_item}.${evidence}.json"
    test -f "$evidence_path"
    rg -q "$evidence_path" "$plan_path"
  done
done
test ! -e docs/superpowers/plans/2026-07-24-release-preflight-merged-source-parity.md
printf '%s\n' 'plan cleanup scan: PASS'
