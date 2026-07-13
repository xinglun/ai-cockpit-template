#!/usr/bin/env python3
"""Structured event logging for AI Cockpit scripts."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = PROJECT_ROOT / "target" / "ai_observability.jsonl"


class AiEventType(str, Enum):
    WORK_ITEM_STARTED = "work_item_started"
    WORK_ITEM_FINISHED = "work_item_finished"
    CHECK_STARTED = "check_started"
    CHECK_PASSED = "check_passed"
    CHECK_FAILED = "check_failed"
    GUARD_VIOLATION = "guard_violation"
    STATUS_GENERATED = "status_generated"


class AiEventLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class AiRunContext:
    work_item_id: str
    run_id: str

    @classmethod
    def create(cls, work_item_id: str) -> AiRunContext:
        return cls(work_item_id=work_item_id, run_id=f"{int(time.time() * 1000):x}")

    @classmethod
    def from_env(cls) -> AiRunContext | None:
        work_item_id = os.environ.get("AI_WORK_ITEM_ID")
        run_id = os.environ.get("AI_RUN_ID")
        if work_item_id and run_id:
            return cls(work_item_id=work_item_id, run_id=run_id)
        return None

    def to_fields(self) -> dict[str, str]:
        return {"workItemId": self.work_item_id, "runId": self.run_id}


@dataclass
class AiEvent:
    event_type: AiEventType
    level: AiEventLevel
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context: AiRunContext | None = None
    check_id: str | None = None
    command: str | None = None
    result: str | None = None
    duration_ms: int | None = None
    severity: str | None = None
    path: str | None = None
    detail: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "timestamp": self.timestamp,
            "eventType": self.event_type.value,
            "level": self.level.value,
            "message": self.message,
        }
        if self.context:
            data.update(self.context.to_fields())
        for key, value in (
            ("checkId", self.check_id),
            ("command", self.command),
            ("result", self.result),
            ("durationMs", self.duration_ms),
            ("severity", self.severity),
            ("path", self.path),
            ("detail", self.detail),
        ):
            if value is not None:
                data[key] = value
        if self.fields:
            data["fields"] = self.fields
        return data


class AiObservabilitySink(Protocol):
    def record(self, event: AiEvent) -> None: ...


class JsonLinesSink:
    def __init__(self, path: Path = DEFAULT_LOG_PATH) -> None:
        self._path = path

    def record(self, event: AiEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event.to_dict(), ensure_ascii=False, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


class AiObservability:
    def __init__(
        self,
        *,
        context: AiRunContext | None = None,
        sinks: list[AiObservabilitySink] | None = None,
    ) -> None:
        self._context = context
        self._sinks = sinks if sinks is not None else [JsonLinesSink()]

    def record(self, event: AiEvent) -> None:
        if event.context is None and self._context is not None:
            event.context = self._context
        for sink in self._sinks:
            try:
                sink.record(event)
            except Exception as exc:
                print(f"[observability] sink failed: {type(sink).__name__}: {exc}", file=sys.stderr)

    def check_started(self, *, check_id: str, command: str | None = None) -> None:
        self.record(
            AiEvent(
                AiEventType.CHECK_STARTED,
                AiEventLevel.INFO,
                f"check started: {check_id}",
                check_id=check_id,
                command=command,
            )
        )

    def check_passed(
        self,
        *,
        check_id: str,
        command: str | None = None,
        duration_ms: int | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        self.record(
            AiEvent(
                AiEventType.CHECK_PASSED,
                AiEventLevel.INFO,
                f"check passed: {check_id}",
                check_id=check_id,
                command=command,
                result="passed",
                duration_ms=duration_ms,
                fields=fields or {},
            )
        )

    def check_failed(
        self,
        *,
        check_id: str,
        command: str | None = None,
        duration_ms: int | None = None,
        detail: str | None = None,
    ) -> None:
        self.record(
            AiEvent(
                AiEventType.CHECK_FAILED,
                AiEventLevel.ERROR,
                f"check failed: {check_id}",
                check_id=check_id,
                command=command,
                result="failed",
                duration_ms=duration_ms,
                detail=detail,
            )
        )

    def guard_violation(self, *, check_id: str, severity: str, path: str, detail: str) -> None:
        level = AiEventLevel.WARNING if severity == "warning" else AiEventLevel.ERROR
        from ai_common import redact_machine_paths

        redacted_path = redact_machine_paths(path)
        self.record(
            AiEvent(
                AiEventType.GUARD_VIOLATION,
                level,
                f"guard violation: {redacted_path}",
                check_id=check_id,
                severity=severity,
                path=redacted_path,
                detail=detail,
            )
        )

    def work_item_started(self, *, fields: dict[str, Any] | None = None) -> None:
        work_item_id = self._context.work_item_id if self._context else "unknown"
        self.record(
            AiEvent(
                AiEventType.WORK_ITEM_STARTED,
                AiEventLevel.INFO,
                f"work item started: {work_item_id}",
                fields=fields or {},
            )
        )

    def work_item_finished(self, *, result: str, duration_ms: int | None = None) -> None:
        work_item_id = self._context.work_item_id if self._context else "unknown"
        level = AiEventLevel.INFO if result == "passed" else AiEventLevel.ERROR
        self.record(
            AiEvent(
                AiEventType.WORK_ITEM_FINISHED,
                level,
                f"work item finished: {work_item_id}",
                result=result,
                duration_ms=duration_ms,
            )
        )

    def status_generated(
        self, *, state: str, output_path: str, fields: dict[str, Any] | None = None
    ) -> None:
        self.record(
            AiEvent(
                AiEventType.STATUS_GENERATED,
                AiEventLevel.INFO,
                f"cockpit status generated: {state}",
                result=state,
                path=output_path,
                fields=fields or {},
            )
        )


def create_observability(work_item_id: str | None = None) -> AiObservability:
    context = AiRunContext.from_env()
    if context is None and work_item_id:
        context = AiRunContext.create(work_item_id)
    return AiObservability(context=context)


def elapsed_ms(start: float) -> int:
    return int((time.time() - start) * 1000)
