---
author: Ray
title: "Real Fixture Repository Evidence"
description: Evidence boundary and lifecycle results for stack fixture experiments.
keywords:
  - fixtures
  - evidence
  - ai-cockpit
---

# Real Fixture Repository Evidence

The TypeScript Web fixture now executes local npm install/build/test/lint/format and lifecycle commands. Its evidence is limited to the checked-out fixture and local toolchain. Provider assets, trusted identity, sandbox isolation, immutable audit, and enterprise compliance remain `not_run`, not inferred from the local result.

The dependency-free `scripts/fixture_harness.py` exercises the adoption lifecycle for Python, TypeScript Web, and Java multi-module fixture manifests. Every fixture records Install → Configure → Normal Work Item → Ambiguous Request → Critical Domain Change → Upgrade → Rollback → Release Check.

The ambiguous and critical-domain phases are expected `blocked` outcomes with a resume condition and policy reference. The harness output is a reviewable evidence bundle, but it is not proof of platform isolation, identity, authentication, immutable audit, enterprise compliance, or production safety.

Python is locally executable through the repository's Python runtime. TypeScript Web and Java multi-module manifests preserve their real stack identity while the harness records that their external toolchains were not invoked. Flutter remains a documented future boundary for this experiment. Performance and multi-agent conflict measurements are explicitly `not_run` or `not_applicable`, never inferred.
