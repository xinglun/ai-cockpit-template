#!/usr/bin/env python3
"""Read-only project fact scanner for AI Cockpit boundary calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ai_common import simple_yaml_lists, simple_yaml_scalars


LANGUAGE_SIGNALS = {
    "python": ("pyproject.toml", "setup.py", "requirements.txt", "**/*.py"),
    "dart": ("pubspec.yaml", "**/*.dart"),
    "java": ("pom.xml", "**/*.java"),
    "kotlin": ("**/*.kt", "**/*.kts"),
    "ruby": ("Gemfile", "**/*.rb"),
    "javascript/typescript": ("package.json", "**/*.ts", "**/*.tsx", "**/*.js"),
    "go": ("go.mod", "**/*.go"),
    "rust": ("Cargo.toml", "**/*.rs"),
    "csharp": ("**/*.csproj", "**/*.cs"),
    "swift": ("Package.swift", "**/*.swift"),
    "php": ("composer.json", "**/*.php"),
}
BUILD_SIGNALS = {
    "gradle": ("build.gradle", "build.gradle.kts", "gradlew"),
    "maven": ("pom.xml",), "flutter": ("pubspec.yaml",), "npm": ("package.json",),
    "python-packaging": ("pyproject.toml", "setup.py"), "cargo": ("Cargo.toml",),
    "go-modules": ("go.mod",), "bundler": ("Gemfile",), "composer": ("composer.json",),
    "dotnet": ("**/*.sln", "**/*.csproj"), "swift-package-manager": ("Package.swift",),
}
INFRA_SIGNALS = {
    "github-actions": (".github/workflows/*.yml", ".github/workflows/*.yaml"),
    "gitlab-ci": (".gitlab-ci.yml",), "docker": ("Dockerfile", "docker-compose.yml", "compose.yaml"),
    "kubernetes": ("k8s/**", "kubernetes/**", "helm/**"), "terraform": ("**/*.tf",),
    "fastlane": ("fastlane/Fastfile",), "database-migrations": ("migrations/**", "db/migrate/**"),
    "code-generation": ("build_runner.yaml", "openapi.yaml", "**/*.g.dart", "**/*.generated.*"),
}
STATE_MANAGEMENT_TERMS = ("riverpod", "provider", "flutter_bloc", "bloc", "redux", "mobx")
NATIVE_ROOTS = ("android", "ios", "macos", "windows", "linux")


def first_evidence(root: Path, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        matches = sorted(path for path in root.glob(pattern) if path.is_file())
        if matches:
            return matches[0].relative_to(root).as_posix()
    return None


def findings(root: Path, signals: dict[str, tuple[str, ...]]) -> list[dict[str, str]]:
    result = []
    for value, patterns in signals.items():
        evidence = first_evidence(root, patterns)
        if evidence:
            result.append({"value": value, "confidence": "high", "evidence": evidence})
    return result


def framework_findings(root: Path) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    pubspec = root / "pubspec.yaml"
    if pubspec.is_file() and "flutter:" in pubspec.read_text(encoding="utf-8", errors="ignore"):
        result.append({"value": "flutter", "confidence": "high", "evidence": "pubspec.yaml:flutter"})
    for build in (root / "build.gradle", root / "build.gradle.kts", root / "pom.xml"):
        if build.is_file() and "spring" in build.read_text(encoding="utf-8", errors="ignore").lower():
            result.append({"value": "spring-boot", "confidence": "high", "evidence": build.name})
            break
    gemfile = root / "Gemfile"
    if gemfile.is_file() and "rails" in gemfile.read_text(encoding="utf-8", errors="ignore").lower():
        result.append({"value": "rails", "confidence": "high", "evidence": "Gemfile"})
    pyproject_text = ""
    for path in (root / "pyproject.toml", root / "requirements.txt"):
        if path.is_file():
            pyproject_text += path.read_text(encoding="utf-8", errors="ignore").lower()
    for name in ("django", "fastapi", "pytorch", "tensorflow"):
        if name in pyproject_text:
            result.append({"value": name, "confidence": "medium", "evidence": "Python dependency manifest"})
    return result


def directory_candidates(root: Path, names: tuple[str, ...], kind: str) -> list[dict[str, str]]:
    result = []
    for name in names:
        path = root / name
        if path.exists():
            result.append({"path": f"{name}/**", "kind": kind, "confidence": "medium", "evidence": name})
    return result


def project_signals(root: Path, infrastructure: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    dependency_text = ""
    for name in ("pubspec.yaml", "package.json", "Gemfile", "pyproject.toml"):
        path = root / name
        if path.is_file():
            dependency_text += path.read_text(encoding="utf-8", errors="ignore").lower()
    state = [
        {"value": term, "confidence": "medium", "evidence": "dependency manifest"}
        for term in STATE_MANAGEMENT_TERMS if term in dependency_text
    ]
    by_value = {item["value"]: item for item in infrastructure}
    native = [
        {"value": name, "confidence": "medium", "evidence": name}
        for name in NATIVE_ROOTS if (root / name).is_dir()
    ]
    return {
        "stateManagement": state,
        "codeGeneration": [by_value["code-generation"]] if "code-generation" in by_value else [],
        "databaseMigrations": [by_value["database-migrations"]] if "database-migrations" in by_value else [],
        "ciReleaseDeployment": [item for item in infrastructure if item["value"] in {"github-actions", "gitlab-ci", "fastlane", "docker", "kubernetes", "terraform"}],
        "native": native,
    }


def scan_project(root: Path) -> dict[str, Any]:
    production = directory_candidates(root, ("src", "lib", "app", "Sources", "cmd", "pkg", "internal"), "production")
    tests = directory_candidates(root, ("tests", "test", "Tests", "spec"), "test")
    generated = directory_candidates(root, ("build", "dist", "generated", ".dart_tool"), "generated")
    critical = directory_candidates(
        root, (".github", "fastlane", "migrations", "db", "infra", "deploy", "release", "security", "android", "ios"), "critical"
    )
    unknowns = []
    if not production:
        unknowns.append("blocking: production roots could not be determined from common directory signals")
    if not tests:
        unknowns.append("blocking: test roots could not be determined from common directory signals")
    coverage = simple_yaml_lists(root / ".ai" / "guards" / "coverage_policy.yaml")
    boundary = simple_yaml_scalars(root / ".ai" / "guards" / "file_boundary.yaml")
    review = simple_yaml_lists(root / ".ai" / "guards" / "ai_review_policy.yaml")
    guard_mismatches = []
    for item in production:
        if item["path"] not in coverage.get("production.include", []):
            guard_mismatches.append({"kind": "production", "path": item["path"], "evidence": item["evidence"]})
    for item in tests:
        if item["path"] not in coverage.get("tests.include", []):
            guard_mismatches.append({"kind": "test", "path": item["path"], "evidence": item["evidence"]})
    for item in generated:
        if f"{item['path']}.boundary" not in boundary:
            guard_mismatches.append({"kind": "generated", "path": item["path"], "evidence": item["evidence"]})
    review_patterns = review.get("requiredReviewChecklist.include", [])
    for item in critical:
        if item["path"] not in review_patterns:
            guard_mismatches.append({"kind": "critical", "path": item["path"], "evidence": item["evidence"]})
    infrastructure = findings(root, INFRA_SIGNALS)
    return {
        "reportVersion": 1,
        "detectedFacts": {
            "languages": findings(root, LANGUAGE_SIGNALS),
            "frameworks": framework_findings(root),
            "buildSystems": findings(root, BUILD_SIGNALS),
            "infrastructure": infrastructure,
        },
        "projectSignals": project_signals(root, infrastructure),
        "suggestedBoundaries": {
            "productionRoots": production,
            "featureRoots": production,
            "testRoots": tests,
            "generatedPaths": generated,
            "criticalPaths": critical,
        },
        "guardMismatches": guard_mismatches,
        "unknowns": unknowns,
        "disclaimer": "Detected facts and suggestions are not approval decisions.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="target/ai_project_doctor_report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = root / args.output
    report = scan_project(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"project doctor report: {output.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
