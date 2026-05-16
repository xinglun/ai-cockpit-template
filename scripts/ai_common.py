#!/usr/bin/env python3
"""Shared helpers for AI Cockpit scripts."""

from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("root must be a JSON object")
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)


def changed_paths() -> list[str]:
    has_head = run_git(["rev-parse", "--verify", "HEAD"])
    paths: list[str] = []
    if has_head.returncode == 0:
        result = run_git(["diff", "--name-only", "HEAD"])
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        paths.extend(line.strip() for line in result.stdout.splitlines() if line.strip())

    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        raise RuntimeError(untracked.stderr.strip())
    paths.extend(line.strip() for line in untracked.stdout.splitlines() if line.strip())
    return sorted(set(paths))


def changed_name_status() -> list[tuple[str, str]]:
    changes: list[tuple[str, str]] = []
    has_head = run_git(["rev-parse", "--verify", "HEAD"])
    if has_head.returncode == 0:
        result = run_git(["diff", "--name-status", "HEAD"])
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                changes.append((parts[0], parts[-1]))

    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        raise RuntimeError(untracked.stderr.strip())
    for line in untracked.stdout.splitlines():
        if line.strip():
            changes.append(("A", line.strip()))
    return changes


def matches(pattern: str, path: str) -> bool:
    normalized = pattern.rstrip("/")
    if normalized.endswith("/**"):
        prefix = normalized[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    if any(ch in normalized for ch in "*?["):
        return fnmatch.fnmatch(path, normalized)
    return path == normalized


def included(path: str, patterns: list[str]) -> bool:
    return any(matches(pattern, path) for pattern in patterns)


def parse_simple_manifest(path: Path) -> dict[str, dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    current: str | None = None
    if not path.exists():
        return manifest
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            current = stripped[:-1].strip('"')
            manifest[current] = {}
            continue
        if current and line.startswith("  ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            manifest[current][key.strip()] = value.strip().strip('"')
    return manifest


def first_match(path: str, manifest: dict[str, dict[str, str]]) -> tuple[str, dict[str, str]] | None:
    found = [(pattern, data) for pattern, data in manifest.items() if matches(pattern, path)]
    if not found:
        return None
    found.sort(key=lambda item: len(item[0]), reverse=True)
    return found[0]


def simple_yaml_lists(path: Path) -> dict[str, list[str]]:
    """Read list values from a tiny YAML subset used by guard policies."""
    result: dict[str, list[str]] = {}
    if not path.exists():
        return result
    stack: list[str] = []
    current_key: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if stripped.startswith("- ") and current_key:
            result.setdefault(current_key, []).append(stripped[2:].strip().strip('"'))
            continue
        if stripped.endswith(":"):
            key = stripped[:-1].strip('"')
            level = indent // 2
            stack = stack[:level]
            stack.append(key)
            current_key = ".".join(stack)
            continue
        current_key = None
    return result


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
