#!/usr/bin/env bash
set -euo pipefail

archive_dir="$(mktemp -d)"
git archive --format=tar --mtime='1970-01-01 00:00:00' --prefix=ai-cockpit/ HEAD^{tree} \
  | python3 -c 'import gzip,sys; out=gzip.GzipFile(fileobj=sys.stdout.buffer, mode="wb", compresslevel=9, mtime=0); out.write(sys.stdin.buffer.read()); out.close()' \
  > "$archive_dir/source.tgz"
archive_hash="$(shasum -a 256 "$archive_dir/source.tgz" | awk '{print $1}')"
declared_hash="$(jq -r '.releaseArchive.sha256' release.json)"
test "$archive_hash" = "$declared_hash"
if tar -tzf "$archive_dir/source.tgz" | rg -q '(^|/)(release|next-release|release-state)\.json$'; then
  echo 'release archive must exclude mutable release projections' >&2
  exit 1
fi
printf '%s\n' 'release archive contract: PASS'
