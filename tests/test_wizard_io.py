from __future__ import annotations

from ai_wizard_io import (
    Action,
    confirm,
    parse_action,
    render_status,
    select,
    text_input,
)


def test_action_parser_supports_help_back_pause_quit_and_answers() -> None:
    assert parse_action("?") is Action.HELP
    assert parse_action("b") is Action.BACK
    assert parse_action("p") is Action.PAUSE
    assert parse_action("q") is Action.QUIT
    assert parse_action("y") is Action.YES
    assert parse_action("n") is Action.NO


def test_non_tty_does_not_wait_for_input() -> None:
    assert (
        confirm("danger", input_fn=lambda: (_ for _ in ()).throw(AssertionError()), is_tty=False)
        is False
    )
    assert (
        text_input("name", input_fn=lambda: (_ for _ in ()).throw(AssertionError()), is_tty=False)
        is None
    )


def test_dangerous_confirmation_defaults_to_no_and_eof_is_safe() -> None:
    assert confirm("danger", input_fn=lambda: "", is_tty=True) is False
    assert confirm("danger", input_fn=lambda: "y", is_tty=True) is True
    assert (
        confirm("danger", input_fn=lambda: (_ for _ in ()).throw(EOFError()), is_tty=True) is False
    )


def test_selection_and_text_input_preserve_control_actions() -> None:
    assert select(["one", "two"], input_fn=lambda: "2", is_tty=True) == 1
    assert select(["one"], input_fn=lambda: "b", is_tty=True) is Action.BACK
    assert text_input("name", input_fn=lambda: "operator", is_tty=True) == "operator"
    assert text_input("name", input_fn=lambda: "q", is_tty=True) is Action.QUIT


def test_status_symbols_are_accessible_and_color_is_optional() -> None:
    assert render_status("passed", color=False) == "[PASS]"
    assert render_status("warning", color=False) == "[WARN]"
    assert render_status("unknown", color=False) == "[UNKNOWN]"
