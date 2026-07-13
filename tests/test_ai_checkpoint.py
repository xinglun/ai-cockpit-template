import ai_checkpoint
from ai_check_diff_ownership import Ownership


def test_intent_context_defaults_when_intent_is_missing():
    assert ai_checkpoint.intent_context({"workItemId": "task"}) == [
        "problem: not provided",
        "constraint: not provided",
        "rationale: not provided",
    ]


def test_intent_context_keeps_values_and_default_placeholders():
    assert ai_checkpoint.intent_context(
        {
            "intent": {
                "problem": "Resolve optional intent compatibility.",
                "constraints": ["Keep V2 backward compatible."],
            }
        }
    ) == [
        "problem: Resolve optional intent compatibility.",
        "constraint: Keep V2 backward compatible.",
        "rationale: not provided",
    ]


def test_checkpoint_ownership_preview_keeps_unresolved_state_visible():
    rendered = ai_checkpoint.format_preview(
        [
            Ownership("docs/guide.md", "unowned", [], "no archive evidence"),
        ]
    )
    assert "[unowned] `docs/guide.md`" in "\n".join(rendered)
