#!/usr/bin/env sh
set -eu

REPO="${AI_COCKPIT_TEMPLATE_REPO:-spirex-ds-dev/ai-cockpit-template}"
# This default is the published release.json tag. Candidate metadata is never
# consulted by Quick Install; use AI_COCKPIT_TEMPLATE_REF explicitly for tests.
REF="${AI_COCKPIT_TEMPLATE_REF:-v0.5.34}"
SOURCE="${AI_COCKPIT_TEMPLATE_SOURCE:-}"
EXPECTED_SHA256="${AI_COCKPIT_TEMPLATE_SHA256:-}"

usage() {
  cat <<'USAGE'
Install AI Cockpit into the current repository.

Usage:
  ./install.sh [installer options]

Environment:
  AI_COCKPIT_TEMPLATE_SOURCE=/path/to/ai-cockpit-template
  AI_COCKPIT_TEMPLATE_REPO=spirex-ds-dev/ai-cockpit-template
  AI_COCKPIT_TEMPLATE_REF=v0.5.34
  AI_COCKPIT_TEMPLATE_SHA256=<expected archive SHA256>

Common options passed through to the Python installer:
  --stack generic|rust|flutter|typescript|python|go|java|android|kotlin|swift|ruby|php|csharp
  --dry-run
  --force
  --upgrade
  --upgrade-with-active
  --replace-glossary
  --create-adoption
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

if SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" 2>/dev/null && pwd); then
  :
else
  SCRIPT_DIR=$(pwd)
fi

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
  TMPDIR_AI_COCKPIT=$(mktemp -d)
  SOURCE="$TMPDIR_AI_COCKPIT/source"
  case "$REPO" in
    http://*|https://*|git@*)
      URL="$REPO"
      ;;
    *)
      URL="https://github.com/$REPO.git"
      ;;
  esac
  echo "Cloning AI Cockpit template from $URL at $REF"
  if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required for remote install." >&2
    exit 2
  fi
  git clone --depth 1 --branch "$REF" --single-branch "$URL" "$SOURCE"
  if [ -n "$EXPECTED_SHA256" ]; then
    ARCHIVE="$TMPDIR_AI_COCKPIT/source.tar.gz"
    git -C "$SOURCE" archive --format=tar.gz --prefix=ai-cockpit/ HEAD -o "$ARCHIVE"
    if command -v sha256sum >/dev/null 2>&1; then
      ACTUAL_SHA256=$(sha256sum "$ARCHIVE" | awk '{print $1}')
    elif command -v shasum >/dev/null 2>&1; then
      ACTUAL_SHA256=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')
    else
      echo "ERROR: SHA256 verification requested but sha256sum or shasum is required." >&2
      exit 2
    fi
    if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
      echo "ERROR: archive SHA256 mismatch for $URL" >&2
      echo "expected: $EXPECTED_SHA256" >&2
      echo "actual:   $ACTUAL_SHA256" >&2
      exit 2
    fi
    echo "Verified archive SHA256: $ACTUAL_SHA256"
  fi
fi

exec python3 "$SOURCE/scripts/install_ai_cockpit.py" --source "$SOURCE" --target "." "$@"
