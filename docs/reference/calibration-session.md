---
author: Ray
title: Calibration Session
description: The adopter-executable ten-stage first-calibration lifecycle.
---

# Calibration Session

`scripts/ai_calibrate.py session` provides the first-calibration scaffold. It is a persisted, reviewable Session; Runtime installation alone is not calibration completion.

## Lifecycle

The Session contains exactly ten ordered stages: repository role, language and stack, source boundaries, test boundaries, generated artifacts, critical paths, quality commands, review requirements, risk and unknowns, and adoption readiness. Japanese (`ja`) is the default language. Each checklist accepts `Y/N`, an alternative/input value, `Unknown`, or `Not Applicable`; `Not Applicable` requires a reason.

```sh
make cockpit-calibrate-session ARGS="start --session-id first-calibration"
make cockpit-calibrate-session ARGS="answer --stage repository_role --answer Y --answer-type yes_no"
make cockpit-calibrate-session ARGS="pause"
make cockpit-calibrate-session ARGS="resume"
make cockpit-calibrate-session ARGS="review"
make cockpit-calibrate-session ARGS="stage-self-check"
make cockpit-calibrate-session ARGS="full-self-check"
make cockpit-calibrate-session ARGS="simulate"
make cockpit-calibrate-session ARGS="confirm --phase reviewer"
make cockpit-calibrate-session ARGS="confirm --phase owner"
make cockpit-calibrate-session ARGS="activate"
```

The JSON Session stores answers, transition events, stage/full self-checks, Governance Simulation, and both human confirmation records. Changing an upstream answer marks completed downstream stages stale; stale evidence is retained but cannot activate a Candidate until revalidated. `back` and `review` do not erase evidence.

Candidate activation writes through a temporary file and atomic replacement only after all ten stages, checks, and both confirmations pass. A failed activation is fail closed and leaves the existing Active configuration unchanged. This scaffold proves repository governance state and evidence only; it is not an enterprise security, identity, sandbox, immutable-audit, or compliance control.
