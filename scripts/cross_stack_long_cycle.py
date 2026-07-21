#!/usr/bin/env python3
"""Aggregate bounded cross-stack fixture and adopter lifecycle evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from external_adopter_long_cycle import run as run_adopter
from fixture_harness import run_fixture


def run(root: Path) -> dict[str, object]:
    """Return one evidence bundle for all local fixtures and the adopter repo."""
    fixtures_root = root / "examples" / "fixtures"
    fixtures = [
        run_fixture(path / "fixture.json")
        for path in sorted(fixtures_root.iterdir())
        if (path / "fixture.json").is_file()
    ]
    return {
        "schemaVersion": 1,
        "fixtures": fixtures,
        "adopterRepository": run_adopter(),
        "evidenceBoundary": {"providerEvidence": "not_run", "enterpriseAssurance": "not_claimed"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(run(args.root.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
