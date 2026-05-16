---
author: Ray
title: "Architecture"
description: AI Cockpit repository layout and component architecture.
keywords:
  - ai-cockpit
  - architecture
  - repository-layout
  - work-item-contract
---

# Architecture

```text
.ai/
  cockpit/
    README.md
    checks.yaml
    current_status.md
  guards/
    backtrack_policy.yaml
    cockpit_status_policy.yaml
    coverage_policy.yaml
    file_boundary.yaml
    file_ownership.yaml
    scope_policy.yaml
    summary_policy.yaml
  work-items/
    _templates/
      work_item_contract.example.json
      work_item_summary.example.json
    active/
    archive/
.cursor/
  rules/
    ai-cockpit.mdc
examples/
  csharp/
  flutter/
  go/
  java/
  kotlin/
  php/
  python/
  ruby/
  rust/
  swift/
  typescript/
docs/
  assets/
    ai-cockpit-demo.gif
scripts/
  ai_archive_work_item.py
  ai_check_backtrack.py
  ai_check_coverage_guard.py
  ai_check_guards.py
  ai_check_scope.py
  ai_check_status.py
  ai_check_summary.py
  ai_check_work_item.py
  ai_common.py
  ai_finish.py
  ai_generate_status.py
  ai_observability.py
  ai_start.py
  install_ai_cockpit.py
templates/
  make/
    Makefile.ai
  stacks/
    *.mk
install.sh
Makefile
AGENTS.md
CLAUDE.md
GEMINI.md
```

## Core Components

| Component | Purpose |
| --- | --- |
| Work Item Contract | Declares task scope, sources, acceptance, verification, and rollback note. |
| Scope Guard | Checks actual git diff against `scope` and `outOfScope`. |
| Backtrack Guard | Reports undeclared removal of tests, snapshots, or Work Item records. |
| Coverage Guard | Reports production changes without matching test changes. |
| Change Summary | Records changed files, checks, risk, generated files, and destructive changes. |
| Cockpit Status | Generates the one-screen status view for the active AI task. |
| Finish Flow | Runs checks and archives the Work Item when ready. |

