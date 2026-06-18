#!/usr/bin/env python3
"""Shared helpers for AI Cockpit scripts."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import subprocess
import shlex
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKS_PATH = PROJECT_ROOT / ".ai" / "cockpit" / "checks.yaml"


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


def current_head() -> str:
    result = run_git(["rev-parse", "--verify", "HEAD"])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def path_fingerprint(path: str) -> str:
    candidate = PROJECT_ROOT / path
    if not candidate.exists():
        return "deleted"
    if not candidate.is_file():
        return "non_file"
    return hashlib.sha256(candidate.read_bytes()).hexdigest()


def _raw_worktree_changes() -> dict[str, str]:
    changes: dict[str, str] = {}
    if current_head():
        result = run_git(["diff", "--name-status", "HEAD"])
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        _merge_name_status(changes, result.stdout)
    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        raise RuntimeError(untracked.stderr.strip())
    for path in untracked.stdout.splitlines():
        if path.strip():
            changes[path.strip()] = "A"
    return changes


def _merge_name_status(changes: dict[str, str], output: str) -> None:
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if status.startswith(("R", "C")) and len(parts) >= 3:
            changes[parts[1]] = "D" if status.startswith("R") else status
            changes[parts[2]] = "A"
        else:
            changes[parts[-1]] = status


def capture_dirty_baseline() -> list[dict[str, str]]:
    return [
        {"path": path, "status": status, "fingerprint": path_fingerprint(path)}
        for path, status in sorted(_raw_worktree_changes().items())
    ]


def active_contract() -> dict[str, Any] | None:
    contracts = sorted((PROJECT_ROOT / ".ai" / "work-items" / "active").glob("*.contract.json"))
    if len(contracts) != 1:
        return None
    try:
        return load_json(contracts[0])
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _baseline(contract: dict[str, Any] | None = None) -> tuple[str, list[dict[str, str]]]:
    data = contract if contract is not None else active_contract() or {}
    base = os.environ.get("AI_BASE_COMMIT", "").strip() or str(data.get("baseCommit", "")).strip()
    dirty = data.get("baselineDirtyPaths", [])
    return base, [item for item in dirty if isinstance(item, dict)] if isinstance(dirty, list) else []


def changed_name_status(
    contract: dict[str, Any] | None = None, *, ignore_baseline_dirty: bool = False
) -> list[tuple[str, str]]:
    changes: dict[str, str] = {}
    head = current_head()
    base, baseline_dirty = _baseline(contract)
    if base:
        valid = run_git(["rev-parse", "--verify", f"{base}^{{commit}}"])
        if valid.returncode != 0:
            raise RuntimeError(f"baseCommit is not a valid commit: {base}")
        if head:
            result = run_git(["diff", "--name-status", f"{base}...HEAD"])
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip())
            _merge_name_status(changes, result.stdout)
    elif head:
        result = run_git(["diff", "--name-status", "HEAD"])
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        _merge_name_status(changes, result.stdout)

    changes.update(_raw_worktree_changes())
    for item in [] if ignore_baseline_dirty else baseline_dirty:
        path = item.get("path")
        fingerprint = item.get("fingerprint")
        if isinstance(path, str) and isinstance(fingerprint, str):
            if path_fingerprint(path) == fingerprint:
                changes.pop(path, None)
            elif path not in changes:
                changes[path] = "D" if not (PROJECT_ROOT / path).exists() else str(item.get("status", "M"))
    return sorted((status, path) for path, status in changes.items())


def changed_paths(contract: dict[str, Any] | None = None, *, ignore_baseline_dirty: bool = False) -> list[str]:
    return [
        path
        for _, path in changed_name_status(contract, ignore_baseline_dirty=ignore_baseline_dirty)
    ]


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
    if not path.exists():
        return {}
    parsed = parse_yaml(path)
    manifest: dict[str, dict[str, str]] = {}
    for k, v in parsed.items():
        if isinstance(v, dict):
            manifest[k] = {str(sub_k): str(sub_v) for sub_k, sub_v in v.items()}
    return manifest


def first_match(path: str, manifest: dict[str, dict[str, str]]) -> tuple[str, dict[str, str]] | None:
    found = [(pattern, data) for pattern, data in manifest.items() if matches(pattern, path)]
    if not found:
        return None
    found.sort(key=lambda item: len(item[0]), reverse=True)
    return found[0]


def parse_yaml(path: Path) -> dict[str, Any]:
    """Parse a subset of YAML used by guard policies, raising ValueError on syntax errors."""
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    root: dict[str, Any] = {}
    # stack holds tuples of (indent, key, container)
    stack: list[tuple[int, str | None, Any]] = [(-2, None, root)]

    for line_idx, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError(f"Syntax Error in {path.name}:{line_idx}: Indentation must be a multiple of 2 spaces.")

        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()

        parent_indent, parent_key, parent_container = stack[-1]

        if stripped.startswith("-"):
            if stripped != "-" and not stripped.startswith("- "):
                raise ValueError(f"Syntax Error in {path.name}:{line_idx}: Invalid list item format.")
            val = stripped[1:].strip().strip('"')

            if isinstance(parent_container, dict):
                if len(stack) < 2:
                    raise ValueError(f"Syntax Error in {path.name}:{line_idx}: List item without a parent key.")
                gp_container = stack[-2][2]
                new_list: list[Any] = []
                gp_container[parent_key] = new_list
                stack[-1] = (parent_indent, parent_key, new_list)
                parent_container = new_list

            if not isinstance(parent_container, list):
                raise ValueError(f"Syntax Error in {path.name}:{line_idx}: List item at invalid indentation level.")
            parent_container.append(val)
        else:
            if ":" not in stripped:
                raise ValueError(f"Syntax Error in {path.name}:{line_idx}: Expected key-value pair or key ending in ':'.")

            key, val = stripped.split(":", 1)
            key = key.strip().strip('"')
            val = val.strip().strip('"')

            if not isinstance(parent_container, dict):
                raise ValueError(f"Syntax Error in {path.name}:{line_idx}: Cannot define key-value pair under a list.")

            if val:
                parent_container[key] = val
            else:
                new_container: dict[str, Any] = {}
                parent_container[key] = new_container
                stack.append((indent, key, new_container))

    return root


def _flatten_lists(obj: Any, prefix: str = "", result: dict[str, list[str]] = None) -> dict[str, list[str]]:
    if result is None:
        result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            if isinstance(v, list):
                result[new_prefix] = v
            else:
                _flatten_lists(v, new_prefix, result)
    return result


def _flatten_scalars(obj: Any, prefix: str = "", result: dict[str, str] = None) -> dict[str, str]:
    if result is None:
        result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str):
                result[new_prefix] = v
            elif not isinstance(v, list):
                _flatten_scalars(v, new_prefix, result)
    return result


def simple_yaml_lists(path: Path) -> dict[str, list[str]]:
    """Read list values from a tiny YAML subset used by guard policies."""
    if not path.exists():
        return {}
    parsed = parse_yaml(path)
    return _flatten_lists(parsed)


def simple_yaml_scalars(path: Path) -> dict[str, str]:
    """Read scalar values from the same intentionally small YAML subset."""
    if not path.exists():
        return {}
    parsed = parse_yaml(path)
    return _flatten_scalars(parsed)


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_check_registry(path: Path = CHECKS_PATH) -> dict[str, dict[str, str]]:
    """Parse the checks section of the repository's small YAML check catalog."""
    registry: dict[str, dict[str, str]] = {}
    try:
        parsed = parse_yaml(path)
    except ValueError:
        return registry
    checks = parsed.get("checks", {})
    if isinstance(checks, dict):
        for check_id, val in checks.items():
            if isinstance(val, dict):
                registry[check_id] = {k: str(v) for k, v in val.items()}
    return registry


def render_check_command(
    check_id: str,
    *,
    contract_path: str,
    summary_path: str,
    registry_path: Path = CHECKS_PATH,
) -> tuple[str, list[str]]:
    registry = load_check_registry(registry_path)
    definition = registry.get(check_id)
    if not definition:
        raise ValueError(f"verification check is not registered: {check_id}")
    template = definition.get("commandTemplate") or definition.get("command")
    if not template:
        raise ValueError(f"registered check has no command: {check_id}")
    command = template.replace("{contractPath}", contract_path).replace("{summaryPath}", summary_path)
    argv = shlex.split(command)
    if not argv or Path(argv[0]).name not in {"make", "gmake"}:
        raise ValueError(f"registered check must invoke an explicit Make target: {check_id}")
    if len(argv) < 2 or argv[1].startswith("-") or "=" in argv[1]:
        raise ValueError(f"registered check must name a Make target: {check_id}")
    return command, argv


def verification_key(item: dict[str, Any]) -> str:
    check_id = item.get("check")
    if non_empty_string(check_id):
        return check_id.strip()
    command = item.get("command")
    return command.strip() if non_empty_string(command) else ""


def redact_machine_paths(value: str) -> str:
    redacted = value.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>")
    redacted = re.sub(r"/(?:Users|home)/[^/\s]+/(?:[^\s\"']+)", "<LOCAL_PATH>", redacted)
    redacted = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+\\(?:[^\s\"']+)", "<LOCAL_PATH>", redacted)
    return redacted


def contains_machine_path(value: str) -> bool:
    return redact_machine_paths(value) != value


def redact_machine_paths_in_data(value: Any) -> Any:
    if isinstance(value, str):
        return redact_machine_paths(value)
    if isinstance(value, list):
        return [redact_machine_paths_in_data(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_machine_paths_in_data(item) for key, item in value.items()}
    return value
