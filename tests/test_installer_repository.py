from __future__ import annotations

import subprocess
from pathlib import Path

from ai_installer_repository import read_repository_facts


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_read_repository_facts_is_read_only_and_captures_adoption_signals(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    (tmp_path / "README.md").write_text("project\n", encoding="utf-8")
    git(tmp_path, "add", "README.md")
    git(
        tmp_path,
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "user.name=Test",
        "commit",
        "-m",
        "initial",
    )
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    facts = read_repository_facts(tmp_path)

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert before == after
    assert facts.branch == "main"
    assert facts.clean is True
    assert facts.active_work_items == ()
    assert facts.to_dict()["root"] == str(tmp_path.resolve())
