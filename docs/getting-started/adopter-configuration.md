---
author: Ray
title: "Adopter Configuration"
description: Required repository-owned configuration before production adoption.
keywords:
  - ai-cockpit
  - adoption
  - codeowners
  - security
---

# Adopter Configuration

AI Cockpit supplies governance mechanics, but it cannot choose the people,
platform identities, or incident policy for an adopting repository. Complete
this checklist after installation and before treating adoption readiness as a
production control.

## Required repository-owned decisions

- Configure `.github/CODEOWNERS` with the real review team or platform identity
  for the target repository. The template repository itself is maintained by
  the authorized personal owner `@RayIori`; an installed target must replace
  that identity and configure at least one required approval before treating
  the review boundary as active. This is not equivalent to an organization
  Team with two independent maintainers.
- Replace the template instructions in `SECURITY.md` with the repository's
  private vulnerability reporting path, supported versions, response
  expectations, and disclosure policy. Do not publish secrets or private
  contact details in this template.
- Record the approved Project Profile and Guard calibration, including the
  repository role, quality commands, coverage boundary, and CI entry points.
- Keep the adopter-owned configuration changes in a separate configuration
  Work Item and commit so the handoff is reviewable.

## Verification

Run the readiness gate after making the adopter-owned replacements:

```sh
make check-ai-adoption-ready
make ai-cockpit-quality
make check-ai-status-consistency
```

The readiness gate intentionally fails for an adopted repository when the
CODEOWNERS owner or SECURITY reporting policy is still a template placeholder.
It does not infer whether a chosen team, platform identity, SLA, or security
process is appropriate; the adopting team owns that decision. A personal
Code Owner and one required approval in the target project do not prove
independent multi-maintainer review or enterprise-trusted governance.

Template maintenance is different: this source repository may retain its
generic placeholders when the explicit template-maintenance execution mode is
used. That exemption must not be copied as an adoption configuration.
