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

The dependency-free `scripts/fixture_harness.py` exercises the adoption lifecycle for Python and fixture manifests. The Java multi-module fixture additionally runs real `javac`/`java` commands across its `core` and `app` modules; its lifecycle records Install → Configure → Normal Work Item → Ambiguous Request → Critical Domain Change → Upgrade → Rollback → Release Check.

Fixture reports may use the same lifecycle vocabulary as `make ai-lifecycle-facts`; local execution evidence is separate from provider assets and enterprise assurance, which remain `not_run`/`not_claimed`.

The ambiguous and critical-domain phases are expected `blocked` outcomes with a resume condition and policy reference. The harness output is a reviewable evidence bundle, but it is not proof of platform isolation, identity, authentication, immutable audit, enterprise compliance, or production safety.

Python is locally executable through the repository's Python runtime. TypeScript Web is locally executable through npm. Java's Maven path is `not_run` when Maven is unavailable, while its dependency-free Java compiler/runtime path remains independently observable. Flutter remains a documented future boundary for this experiment. Performance and multi-agent conflict measurements are explicitly `not_run` or `not_applicable`, never inferred.
