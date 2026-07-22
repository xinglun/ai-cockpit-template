"""Evidence boundary for deterministic installer action summaries."""

from collections.abc import Sequence


def action_counts(actions: Sequence[object]) -> tuple[int, int]:
    writes = sum(
        getattr(item, "kind", "") in {"write", "overwrite", "append", "replace"} for item in actions
    )
    skips = sum(getattr(item, "kind", "") == "skip" for item in actions)
    return writes, skips
