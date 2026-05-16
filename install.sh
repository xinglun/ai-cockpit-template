#!/usr/bin/env sh
set -eu

REPO="${AI_COCKPIT_TEMPLATE_REPO:-OWNER/ai-cockpit-template}"
REF="${AI_COCKPIT_TEMPLATE_REF:-main}"
SOURCE="${AI_COCKPIT_TEMPLATE_SOURCE:-}"

usage() {
  cat <<'USAGE'
Install AI Cockpit into the current repository.

Usage:
  ./install.sh [installer options]

Environment:
  AI_COCKPIT_TEMPLATE_SOURCE=/path/to/ai-cockpit-template
  AI_COCKPIT_TEMPLATE_REPO=OWNER/ai-cockpit-template
  AI_COCKPIT_TEMPLATE_REF=main

Common options passed through to the Python installer:
  --stack generic|rust|flutter|typescript|python
  --dry-run
  --force
  --with-examples
  --update-makefile
USAGE
}

for arg in "$@"; do
  case "$arg" in
    -h|--help)
      usage
      exit 0
      ;;
  esac
done

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || pwd)

if [ -z "$SOURCE" ] && [ -f "$SCRIPT_DIR/scripts/install_ai_cockpit.py" ]; then
  SOURCE="$SCRIPT_DIR"
fi

cleanup() {
  if [ "${TMPDIR_AI_COCKPIT:-}" ] && [ -d "$TMPDIR_AI_COCKPIT" ]; then
    rm -rf "$TMPDIR_AI_COCKPIT"
  fi
}
trap cleanup EXIT

if [ -z "$SOURCE" ]; then
  if [ "$REPO" = "OWNER/ai-cockpit-template" ]; then
    echo "ERROR: set AI_COCKPIT_TEMPLATE_REPO=OWNER/ai-cockpit-template before using curl-pipe install." >&2
    exit 2
  fi
  TMPDIR_AI_COCKPIT=$(mktemp -d)
  URL="https://github.com/$REPO/archive/refs/heads/$REF.tar.gz"
  echo "Downloading AI Cockpit template from $URL"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$URL" | tar -xz -C "$TMPDIR_AI_COCKPIT" --strip-components=1
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- "$URL" | tar -xz -C "$TMPDIR_AI_COCKPIT" --strip-components=1
  else
    echo "ERROR: curl or wget is required for remote install." >&2
    exit 2
  fi
  SOURCE="$TMPDIR_AI_COCKPIT"
fi

exec python3 "$SOURCE/scripts/install_ai_cockpit.py" --source "$SOURCE" --target "." "$@"

