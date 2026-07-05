---
author: Ray
title: "AI Governance Workspace"
description: Stable entrypoint for repository AI governance files and required workflow documentation.
---

# AI Governance Workspace

AI Cockpit is a Repository Governance Layer for AI-assisted Software Development. This workspace contains governance contracts, policies, and generated status.

Read these files before changing the repository:

1. `.ai/cockpit/README.md` for the Work Item lifecycle and required commands.
2. [`.ai/cockpit/README.ja.md`](cockpit/README.ja.md) for the Japanese runtime workflow guide.
3. `.ai/glossary.md` for canonical product and governance terminology.
4. The active Contract and Summary under `.ai/work-items/active/`.
5. `.ai/cockpit/adoption.md` when installing AI Cockpit into another repository.

## Key Concepts

- **Intent**: Why work exists — problem, constraints, rationale (optional but recommended)
- **Contract**: What should change — scope, acceptance, verification
- **Implementation**: What actually changed
- **Verification**: Does it meet requirements?
- **Summary**: Did we achieve the intended goal? Intent alignment validation

Guard policies live under `.ai/guards/`. Generated Cockpit Status must be updated through the Make targets documented in `.ai/cockpit/README.md`, not edited manually.
