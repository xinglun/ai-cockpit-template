#!/usr/bin/env python3
"""Generate and validate project boundary calibration Profiles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ai_project_profile import BOUNDARY_KEYS, FACT_KEYS, load_profile


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def values(items: Any, key: str) -> list[str]:
    if not isinstance(items, list):
        return []
    return sorted({str(item[key]) for item in items if isinstance(item, dict) and item.get(key)})


def render_key_list(lines: list[str], indent: str, key: str, items: list[str]) -> None:
    if not items:
        lines.append(f"{indent}{key}: []")
        return
    lines.append(f"{indent}{key}:")
    lines.extend(f"{indent}  - {quote(item)}" for item in items)


def proposed_profile(report: dict[str, Any]) -> str:
    facts = report.get("detectedFacts", {})
    suggestions = report.get("suggestedBoundaries", {})
    lines = [
        "# Generated proposal. Review facts and suggestions; do not treat this file as approved.",
        "version: 1",
        "repositoryRole: template",
        "",
        "detectedFacts:",
    ]
    for key in FACT_KEYS:
        render_key_list(
            lines, "  ", key, values(facts.get(key, []) if isinstance(facts, dict) else [], "value")
        )
    lines.extend(["", "suggestedBoundaries:"])
    for key in BOUNDARY_KEYS:
        render_key_list(
            lines,
            "  ",
            key,
            values(suggestions.get(key, []) if isinstance(suggestions, dict) else [], "path"),
        )
    lines.extend(["", "approvedBoundaries:"])
    for key in BOUNDARY_KEYS:
        render_key_list(lines, "  ", key, [])
    lines.extend(["", "reviewRequirements: []", ""])
    render_key_list(
        lines,
        "",
        "unknowns",
        [str(item) for item in report.get("unknowns", []) if isinstance(item, str)],
    )
    evidence = []
    if isinstance(facts, dict):
        for category in FACT_KEYS:
            for item in facts.get(category, []):
                if isinstance(item, dict):
                    evidence.append(
                        f"{category}:{item.get('value', '')}|confidence:{item.get('confidence', '')}|evidence:{item.get('evidence', '')}"
                    )
    lines.append("")
    render_key_list(lines, "", "evidence", evidence)
    lines.extend(["", "approval:", "  reviewed: false", '  reviewedBy: ""', '  reason: ""'])
    return "\n".join(lines) + "\n"


def generate(root: Path, report_path: Path, output: Path) -> int:
    if output.exists():
        print(f"ERROR: refusing to overwrite calibration proposal: {output}", file=sys.stderr)
        return 2
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to read Doctor report: {exc}", file=sys.stderr)
        return 2
    if report.get("reportVersion") != 1:
        print("ERROR: unsupported Doctor report version", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(proposed_profile(report), encoding="utf-8")
    print(f"calibration proposal: {output.relative_to(root)}")
    print(
        "Review and copy approved values into .ai/project_profile.yaml; this command does not modify Guards."
    )
    return 0


def validate(path: Path, *, confirmed: bool) -> int:
    _, issues = load_profile(path, require_approval=confirmed)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    print(f"project Profile validation passed: {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--root", default=".")
    generate_parser.add_argument("--report", default="target/ai_project_doctor_report.json")
    generate_parser.add_argument("--output", default=".ai/project_profile.proposed.yaml")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--profile", default=".ai/project_profile.proposed.yaml")
    validate_parser.add_argument("--confirmed", action="store_true")
    args = parser.parse_args()
    if args.command == "generate":
        root = Path(args.root).resolve()
        return generate(root, root / args.report, root / args.output)
    return validate(Path(args.profile), confirmed=args.confirmed)


if __name__ == "__main__":
    raise SystemExit(main())
