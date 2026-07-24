---
author: Ray
title: "Wizard IO and Localization"
description: TTY-safe input controls and exact-parity Wizard message resources.
keywords:
  - interactive-wizard
  - localization
  - accessibility
---

# Wizard IO and Localization

`ai_wizard_io` is the shared, fail-closed input boundary for later Wizard
steps. Non-TTY execution never waits for input; blank, EOF, and Ctrl+C do not
confirm dangerous actions. Back, Pause, Quit, and Help are represented as
explicit `Action` values, and status output remains readable without color.

`ai_wizard_localization` normalizes the Wizard's `ja`, `en`, and `zh-CN`
language aliases independently from project documentation language. Resources
are checked for exact keys and `{placeholder}` parity before user-visible use;
unsupported languages raise an error instead of silently falling back.
