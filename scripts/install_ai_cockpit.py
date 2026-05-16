#!/usr/bin/env python3
"""Install AI Cockpit into an existing repository."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


STACKS = {"generic", "rust", "flutter", "typescript", "python"}
SCRIPT_NAMES = {
    "ai_archive_work_item.py",
    "ai_check_backtrack.py",
    "ai_check_coverage_guard.py",
    "ai_check_guards.py",
    "ai_check_scope.py",
    "ai_check_status.py",
    "ai_check_summary.py",
    "ai_check_work_item.py",
    "ai_common.py",
    "ai_finish.py",
    "ai_generate_status.py",
    "ai_observability.py",
    "ai_start.py",
}
AGENT_MARKER = "<!-- AI_COCKPIT_SECTION -->"


@dataclass(frozen=True)
class Action:
    kind: str
    path: Path
    detail: str


class Installer:
    def __init__(
        self,
        *,
        source: Path,
        target: Path,
        stack: str,
        force: bool,
        dry_run: bool,
        with_examples: bool,
        update_makefile: bool,
    ) -> None:
        self.source = source.resolve()
        self.target = target.resolve()
        self.stack = stack
        self.force = force
        self.dry_run = dry_run
        self.with_examples = with_examples
        self.update_makefile = update_makefile
        self.actions: list[Action] = []

    def install(self) -> int:
        if not self.source.exists():
            print(f"ERROR: source template does not exist: {self.source}", file=sys.stderr)
            return 2
        if self.stack not in STACKS:
            print(f"ERROR: unsupported stack {self.stack}; expected one of {sorted(STACKS)}", file=sys.stderr)
            return 2
        self.target.mkdir(parents=True, exist_ok=True)

        self.copy_tree(".ai")
        self.copy_scripts()
        self.copy_file("templates/make/Makefile.ai", "Makefile.ai")
        self.copy_file(f"templates/stacks/{self.stack}.mk", "Makefile.ai.stack")
        if self.with_examples:
            self.copy_tree("examples")
        self.install_agent_doc("AGENTS.md")
        self.install_agent_doc("GEMINI.md")
        if self.update_makefile:
            self.append_makefile_include()

        self.print_summary()
        return 0

    def record(self, kind: str, path: Path, detail: str) -> None:
        self.actions.append(Action(kind, path, detail))
        print(f"{kind}: {path.relative_to(self.target) if path.is_relative_to(self.target) else path} - {detail}")

    def copy_tree(self, relative: str) -> None:
        src = self.source / relative
        dst = self.target / relative
        if not src.exists():
            return
        for item in src.rglob("*"):
            if item.is_dir():
                continue
            rel = item.relative_to(src)
            self.copy_path(item, dst / rel)

    def copy_scripts(self) -> None:
        for name in sorted(SCRIPT_NAMES):
            self.copy_path(self.source / "scripts" / name, self.target / "scripts" / name, executable=True)

    def copy_file(self, src_relative: str, dst_relative: str) -> None:
        self.copy_path(self.source / src_relative, self.target / dst_relative)

    def copy_path(self, src: Path, dst: Path, *, executable: bool = False) -> None:
        if dst.exists() and not self.force:
            self.record("skip", dst, "already exists")
            return
        self.record("write" if not dst.exists() else "overwrite", dst, f"from {src.relative_to(self.source)}")
        if self.dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if executable:
            dst.chmod(dst.stat().st_mode | 0o111)

    def install_agent_doc(self, name: str) -> None:
        src = self.source / name
        dst = self.target / name
        if not dst.exists():
            self.copy_path(src, dst)
            return
        text = dst.read_text(encoding="utf-8")
        if AGENT_MARKER in text:
            self.record("skip", dst, "AI Cockpit section already present")
            return
        section = self.agent_section(src)
        self.record("append", dst, "add AI Cockpit section")
        if self.dry_run:
            return
        with dst.open("a", encoding="utf-8") as handle:
            if text and not text.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + section)

    def agent_section(self, src: Path) -> str:
        title = "AI Cockpit Rules"
        body = src.read_text(encoding="utf-8").strip()
        return f"{AGENT_MARKER}\n\n## {title}\n\n{body}\n"

    def append_makefile_include(self) -> None:
        dst = self.target / "Makefile"
        include_line = "include Makefile.ai"
        if not dst.exists():
            self.record("write", dst, "create Makefile with AI Cockpit include")
            if not self.dry_run:
                dst.write_text(f"{include_line}\n", encoding="utf-8")
            return
        text = dst.read_text(encoding="utf-8")
        if include_line in text:
            self.record("skip", dst, "Makefile.ai already included")
            return
        self.record("append", dst, "include Makefile.ai")
        if self.dry_run:
            return
        with dst.open("a", encoding="utf-8") as handle:
            if text and not text.endswith("\n"):
                handle.write("\n")
            handle.write(f"\n{include_line}\n")

    def print_summary(self) -> None:
        writes = sum(1 for action in self.actions if action.kind in {"write", "overwrite", "append"})
        skips = sum(1 for action in self.actions if action.kind == "skip")
        print("")
        print(f"AI Cockpit install {'dry run ' if self.dry_run else ''}complete: {writes} write/append action(s), {skips} skipped.")
        print("")
        print("Next steps:")
        if not self.update_makefile:
            print("  1. Add this line to your Makefile: include Makefile.ai")
            print("  2. Run: make ai-start TASK=example_change TITLE=\"Example change\" MODE=code")
            print("  3. Edit the generated Contract before changing project files.")
            print("  4. Finish with: make ai-finish TASK=example_change")
        else:
            print("  1. Run: make ai-start TASK=example_change TITLE=\"Example change\" MODE=code")
            print("  2. Edit the generated Contract before changing project files.")
            print("  3. Finish with: make ai-finish TASK=example_change")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install AI Cockpit into an existing repository.")
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1]), help="Path to the ai-cockpit-template source.")
    parser.add_argument("--target", default=".", help="Target repository root.")
    parser.add_argument("--stack", default="generic", choices=sorted(STACKS), help="Project stack preset.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing AI Cockpit files.")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing files.")
    parser.add_argument("--with-examples", action="store_true", help="Copy examples/ into the target repository.")
    parser.add_argument("--update-makefile", action="store_true", help="Append include Makefile.ai to the target Makefile.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return Installer(
        source=Path(args.source),
        target=Path(args.target),
        stack=args.stack,
        force=args.force,
        dry_run=args.dry_run,
        with_examples=args.with_examples,
        update_makefile=args.update_makefile,
    ).install()


if __name__ == "__main__":
    sys.exit(main())
