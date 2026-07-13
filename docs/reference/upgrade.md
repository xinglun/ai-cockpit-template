---
author: Ray
title: "Upgrade"
description: Upgrade guide for an existing AI Cockpit installation.
keywords:
  - ai-cockpit
  - upgrade
  - migration
  - release
---

# Upgrade

Use `--upgrade` when the target repository already contains AI Cockpit files and you want the managed runtime, policy, and marker files replaced in a controlled way.

```sh
CURRENT_VERSION="${CURRENT_VERSION:?set CURRENT_VERSION to the installed release tag}"
TARGET_VERSION="${TARGET_VERSION:?set TARGET_VERSION to a newer release tag}"
test "$TARGET_VERSION" != "$CURRENT_VERSION"
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL "${AI_COCKPIT_TEMPLATE_RAW_BASE:?set AI_COCKPIT_TEMPLATE_RAW_BASE to the matching raw-content base}/$TARGET_VERSION/install.sh" -o "$INSTALLER"
AI_COCKPIT_TEMPLATE_REF="$TARGET_VERSION" \
  sh "$INSTALLER" --upgrade --stack rust
```

Replace the example repository with the real release source for your installation. If you are upgrading a mirrored or private deployment, point the installer at that configured source instead of the public example.

The installer rejects distribution or Contract-schema downgrades. Never set `TARGET_VERSION` lower than the version recorded in the installed `.ai/cockpit/version.json`.

By default, upgrade stops before writing if `.ai/work-items/active/` contains Work Item JSON. Finish and archive the active task first. `--upgrade-with-active` is an explicit high-risk override for recovery scenarios where changing governance semantics during a task is intentional.

Before replacement, managed files are copied under `.ai/cockpit/upgrade-backups/<timestamp>/`. Despite the historical directory name, the installer also uses it as a transaction rollback area when a first installation appends to an existing file such as `Makefile`. Review and remove successful-upgrade backups when they are no longer needed.

If you did not use `--update-makefile`, add this line to your project Makefile:

```make
include Makefile.ai
```

Use [Distribution](distribution.md) for installer options and release capability details, and [Troubleshooting](troubleshooting.md) for recovery paths when an upgrade does not complete cleanly.

## Cursor rule default

New installations ship `.cursor/rules/ai-cockpit.mdc` with `alwaysApply: false`. Read-only investigation no longer forces a Work Item by default. Teams that want stricter enforcement can enable **Always Apply** in Cursor rule settings or set `alwaysApply: true` after reviewing local workflow impact.

Existing installations keep their current rule file until you upgrade or merge the managed `.cursor` tree from a newer AI Cockpit release.
