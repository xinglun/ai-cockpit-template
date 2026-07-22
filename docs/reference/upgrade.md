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

An upgrade is a repository change, not a Ready signal. Run Impact Assessment before any recalibration proposal. Candidate activation and preservation of the old Active Configuration are planned capabilities until the corresponding Work Item evidence exists; runtime installation alone never proves calibration completion. See the [Capability Truth Matrix](capability-truth-matrix.md).

Use `--upgrade` when the target repository already contains AI Cockpit files and you want the managed runtime, policy, and marker files replaced in a controlled way. Treat the upgrade as its own adopter-project Work Item and dedicated branch. Record the adopter remote/default branch/base commit and the target release tag before changing files.

Upgrade is local preparation only. Review the Contract and upgrade diff first, then obtain separate human approval for commit and push. The upgrade PR must be reviewed and merged manually. After merge, obtain a final human approval before running `make ai-close-work-item TASK=<upgrade-task>`. Do not use automatic merge or automatic branch deletion. The installer itself never performs any of these external Git actions.

An upgrade now creates `upgrade_ai_cockpit` Contract and Summary records in the target repository. When the adopter has a discoverable remote default branch, it prepares `upgrade/ai-cockpit` (or `AI_COCKPIT_UPGRADE_BRANCH`) from that base; local-only repositories retain their existing behavior. The records capture source/target version metadata, managed-file changes, and the timestamped rollback backup root. The installer does not commit, push, open or merge a PR, or delete the review branch.

If a remote exists but its default branch cannot be established from remote HEAD, upgrade fails closed. Supply both `--base-remote <remote>` and `--base-branch <branch>` to provide explicit base evidence; the resulting Contract records both values and the base commit.

```sh
CURRENT_VERSION="${CURRENT_VERSION:?set CURRENT_VERSION to the installed release tag}"
TARGET_VERSION="${TARGET_VERSION:?set TARGET_VERSION to a newer release tag}"
test "$TARGET_VERSION" != "$CURRENT_VERSION"
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL "${AI_COCKPIT_TEMPLATE_RAW_BASE:?set AI_COCKPIT_TEMPLATE_RAW_BASE to the matching raw-content base}/$TARGET_VERSION/install.sh" -o "$INSTALLER"
AI_COCKPIT_TEMPLATE_REPO="${AI_COCKPIT_TEMPLATE_REPO:?set AI_COCKPIT_TEMPLATE_REPO to the release source}" \
AI_COCKPIT_TEMPLATE_REF="$TARGET_VERSION" \
  sh "$INSTALLER" --upgrade --stack rust
```

Replace the example repository with the real release source for your installation. If you are upgrading a mirrored or private deployment, point the installer at that configured source instead of the public example.

The installer rejects distribution, Contract-schema, or release semver downgrades. Never set `TARGET_VERSION` lower than the release semver recorded in the installed `.ai/cockpit/version.json`.

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
### Upgrade conflict report

When an upgrade finds a project-owned or diverged governance file, it writes
`.ai/cockpit/upgrade-conflict-report.json` with the path classification, diff
summary, and recommendation, then stops. Review the report and rerun with
`--confirm-upgrade-conflicts` only after deciding that the preserved target
content is correct. Missing or malformed reports must be treated as a failed
upgrade; the installer never silently overwrites these files.
