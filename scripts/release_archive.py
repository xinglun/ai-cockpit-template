#!/usr/bin/env python3
"""Build the source-bound release archive with stable bytes across runners."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import subprocess
import tarfile
from pathlib import Path


def _git_archive_members(root: Path, source_commit: str) -> list[tarfile.TarInfo]:
    result = subprocess.run(  # nosec B603 B607
        [
            "git",
            "-C",
            str(root),
            "archive",
            "--format=tar",
            "--prefix=ai-cockpit/",
            f"{source_commit}^{{tree}}",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
        return archive.getmembers()


def canonical_tar(root: Path, source_commit: str) -> bytes:
    """Serialize Git-selected paths using Python-owned stable tar metadata."""
    members = _git_archive_members(root, source_commit)
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for member in members:
            stable = tarfile.TarInfo(member.name)
            stable.mode = member.mode
            stable.type = member.type
            stable.linkname = member.linkname
            stable.uid = stable.gid = 0
            stable.uname = stable.gname = ""
            stable.mtime = 0
            if member.isfile():
                path = member.name.removeprefix("ai-cockpit/")
                content = subprocess.run(  # nosec B603 B607
                    ["git", "-C", str(root), "show", f"{source_commit}:{path}"],
                    check=True,
                    stdout=subprocess.PIPE,
                ).stdout
                stable.size = len(content)
                archive.addfile(stable, io.BytesIO(content))
            else:
                stable.size = 0
                archive.addfile(stable)
    return output.getvalue()


def canonical_archive_bytes(root: Path, source_commit: str) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", compresslevel=9, mtime=0) as compressor:
        compressor.write(canonical_tar(root, source_commit))
    return output.getvalue()


def canonical_source_tree(root: Path, source_commit: str) -> str:
    return hashlib.sha256(canonical_tar(root, source_commit)).hexdigest()


def canonical_archive_sha(root: Path, source_commit: str) -> str:
    return hashlib.sha256(canonical_archive_bytes(root, source_commit)).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_bytes(canonical_archive_bytes(args.root.resolve(), args.source_commit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
