#!/usr/bin/env sh
set -eu

REPO="${AI_COCKPIT_TEMPLATE_REPO:-spirex-ds-dev/ai-cockpit-template}"
# This default is the published release.json tag. Candidate metadata is never
# consulted by Quick Install; use AI_COCKPIT_TEMPLATE_REF explicitly for tests.
REF="${AI_COCKPIT_TEMPLATE_REF:-v0.5.41}"
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
  AI_COCKPIT_TEMPLATE_REF=v0.5.41
  AI_COCKPIT_TEMPLATE_SHA256=<optional assertion; release.json remains authoritative>

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
  # The release contract, not a caller-provided flag, is the default trust root.
  # The optional URL override exists only for deterministic contract tests.
  if [ -n "${AI_COCKPIT_TEMPLATE_RELEASE_ASSET_URL:-}" ] && [ -n "$EXPECTED_SHA256" ]; then
    python3 "$SOURCE/scripts/verify_quick_install_release.py" \
      --root "$SOURCE" --ref "$REF" \
      --asset-url "$AI_COCKPIT_TEMPLATE_RELEASE_ASSET_URL" \
      --expected-archive-sha256 "$EXPECTED_SHA256"
  elif [ -n "${AI_COCKPIT_TEMPLATE_RELEASE_ASSET_URL:-}" ]; then
    python3 "$SOURCE/scripts/verify_quick_install_release.py" \
      --root "$SOURCE" --ref "$REF" \
      --asset-url "$AI_COCKPIT_TEMPLATE_RELEASE_ASSET_URL"
  elif [ -n "$EXPECTED_SHA256" ]; then
    python3 "$SOURCE/scripts/verify_quick_install_release.py" \
      --root "$SOURCE" --ref "$REF" \
      --expected-archive-sha256 "$EXPECTED_SHA256"
  else
    python3 "$SOURCE/scripts/verify_quick_install_release.py" --root "$SOURCE" --ref "$REF"
  fi
fi

exec python3 "$SOURCE/scripts/install_ai_cockpit.py" --source "$SOURCE" --target "." "$@"
