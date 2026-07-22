"""Transaction boundary vocabulary for installer actions."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TransactionAction:
    kind: str
    path: Path
    detail: str
