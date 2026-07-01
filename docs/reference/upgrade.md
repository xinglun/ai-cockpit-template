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
CURRENT_VERSION=v0.5.14
TARGET_VERSION='<release-tag-newer-than-current>'
test "$TARGET_VERSION" != "$CURRENT_VERSION"
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL "https://raw.githubusercontent.com/xinglun/ai-cockpit-template/$TARGET_VERSION/install.sh" -o "$INSTALLER"
AI_COCKPIT_TEMPLATE_REF="$TARGET_VERSION" \
  sh "$INSTALLER" --upgrade --stack rust
```

The installer rejects distribution or Contract-schema downgrades. Never set `TARGET_VERSION` lower than the version recorded in the installed `.ai/cockpit/version.json`.

By default, upgrade stops before writing if `.ai/work-items/active/` contains Work Item JSON. Finish and archive the active task first. `--upgrade-with-active` is an explicit high-risk override for recovery scenarios where changing governance semantics during a task is intentional.

Before replacement, managed files are copied under `.ai/cockpit/upgrade-backups/<timestamp>/`. Despite the historical directory name, the installer also uses it as a transaction rollback area when a first installation appends to an existing file such as `Makefile`. Review and remove successful-upgrade backups when they are no longer needed.

If you did not use `--update-makefile`, add this line to your project Makefile:

```make
include Makefile.ai
```

Use [Distribution](distribution.md) for installer options and release capability details, and [Troubleshooting](troubleshooting.md) for recovery paths when an upgrade does not complete cleanly.
