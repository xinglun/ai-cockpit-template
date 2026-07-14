---
author: Ray
title: "Supply-Chain SBOM and Release Trust Design"
description: "CycloneDX、漏洞身份映射与发布证据一致性的修复设计。"
keywords:
  - sbom
  - cyclonedx
  - supply-chain
  - release
---

# Supply-Chain SBOM and Release Trust Design

## Goal

Make the template's supply-chain evidence semantically correct, component-addressable, and explicit about the remaining external release trust boundary.

## Design

`check_supply_chain.py` will parse each pip-compile lock entry as a structured record. The parser removes continuation syntax from the version, collects all artifact hashes, and preserves direct/transitive attribution. SBOM generation will use `cyclonedx-python-lib`'s model and JSON serializer, producing CycloneDX 1.5 metadata, stable component references, PyPI package URLs, hashes, tool metadata, and dependency edges. GitHub Actions will remain represented as components with stable references and repository URLs.

The vulnerability command will run `pip-audit` against the lock, normalize package names using the same identity function as the SBOM builder, and attach each finding to the matching component reference. An unmappable finding is an error so the scan cannot silently report a vulnerability outside the SBOM identity graph.

Release evidence will add a generated digest manifest that covers the lock, SBOM, provenance, and installer. The checker will validate the manifest and provenance linkage. The documentation will state that this proves repository-internal consistency only; cryptographic signing or Sigstore attestation must be supplied by the publishing environment and is not fabricated by this repository.

## Testing and verification

Tests will first reproduce the trailing backslash and missing hash mapping, then cover CycloneDX fields, dependency references, vulnerability mapping, and manifest drift. Baseline JSON files and `release.json` will be regenerated only through the supply-chain command. The AI Cockpit checks, Python tests, format/lint/type checks, and supply-chain checks listed in the Contract will be run before finish.

## Constraints

- No private signing key or credential is stored in the repository.
- Generated status and evidence files are produced by commands.
- Existing release-tag/source-commit behavior remains backward compatible.
- The change stays within the Contract scope.
