---
author: Ray
title: "Installation Detection Boundary"
description: Read-only repository facts and deterministic Installation Plan boundary for the interactive installer.
keywords:
  - installer
  - installation-plan
  - read-only-detection
---

# Installation Detection Boundary

Work Item 3 exposes `ai_installer_detection.collect_installation_detection()` as a
read-only adapter for the future Installation Wizard. It captures repository and
toolchain facts, distinguishes `new_adoption` from `upgrade`, and returns a
deterministic `InstallationPlan` containing the recommendation, impact,
examples, write boundary, expected result, stop condition, and operator
checklist.

The adapter does not create branches, write files, create Work Items, or perform
rollback. After explicit human confirmation, the existing `Installer` in
`scripts/install_ai_cockpit.py` remains the sole transaction authority.

Use `serialize_plan(plan)` when a stable JSON representation is needed. The
serialized output sorts keys and preserves checklist/example order so it can be
used in tests and evidence without depending on dictionary insertion order.
