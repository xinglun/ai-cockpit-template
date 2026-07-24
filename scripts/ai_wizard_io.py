"""TTY-safe, fail-closed input and accessible output primitives."""

from __future__ import annotations

from enum import Enum
from typing import Callable, Sequence, TextIO


class Action(Enum):
    YES = "yes"
    NO = "no"
    BACK = "back"
    PAUSE = "pause"
    QUIT = "quit"
    HELP = "help"


InputFn = Callable[[], str]


def parse_action(value: str) -> Action | None:
    """Parse a control key; unknown text is left for field-specific parsing."""
    normalized = value.strip().lower()
    return {
        "y": Action.YES,
        "yes": Action.YES,
        "n": Action.NO,
        "no": Action.NO,
        "b": Action.BACK,
        "back": Action.BACK,
        "p": Action.PAUSE,
        "pause": Action.PAUSE,
        "q": Action.QUIT,
        "quit": Action.QUIT,
        "?": Action.HELP,
        "h": Action.HELP,
        "help": Action.HELP,
    }.get(normalized)


def _read(input_fn: InputFn) -> str | None:
    try:
        return input_fn()
    except (EOFError, KeyboardInterrupt):
        return None


def confirm(
    prompt: str, *, input_fn: InputFn = input, is_tty: bool = True, dangerous: bool = True
) -> bool:
    """Read confirmation, returning ``False`` for non-TTY, blank, EOF, or interruption."""
    del prompt
    if not is_tty:
        return False
    value = _read(input_fn)
    if value is None or not value.strip():
        return False
    action = parse_action(value)
    return action is Action.YES and not (dangerous and action is not Action.YES)


def select(
    options: Sequence[str], *, input_fn: InputFn = input, is_tty: bool = True
) -> int | Action | None:
    """Return a zero-based option index or an explicit control action."""
    if not is_tty:
        return None
    value = _read(input_fn)
    if value is None:
        return Action.QUIT
    action = parse_action(value)
    if action in {Action.BACK, Action.PAUSE, Action.QUIT, Action.HELP}:
        return action
    try:
        index = int(value.strip()) - 1
    except ValueError:
        return None
    return index if 0 <= index < len(options) else None


def text_input(
    prompt: str, *, input_fn: InputFn = input, is_tty: bool = True
) -> str | Action | None:
    """Return text or a control action without ever blocking in non-TTY mode."""
    del prompt
    if not is_tty:
        return None
    value = _read(input_fn)
    if value is None:
        return Action.QUIT
    action = parse_action(value)
    if action in {Action.BACK, Action.PAUSE, Action.QUIT, Action.HELP}:
        return action
    return value.strip()


def render_status(status: str, *, color: bool = False) -> str:
    """Render accessible ASCII status text, optionally with ANSI color."""
    labels = {
        "passed": "[PASS]",
        "warning": "[WARN]",
        "failed": "[FAIL]",
        "unknown": "[UNKNOWN]",
        "skipped": "[SKIP]",
    }
    label = labels.get(status.lower(), "[INFO]")
    if not color:
        return label
    codes = {"[PASS]": "\033[32m", "[WARN]": "\033[33m", "[FAIL]": "\033[31m"}
    return f"{codes.get(label, '')}{label}\033[0m"


def stream_is_tty(stream: TextIO) -> bool:
    """Return false when a stream is absent or not connected to a TTY."""
    return bool(getattr(stream, "isatty", lambda: False)())
