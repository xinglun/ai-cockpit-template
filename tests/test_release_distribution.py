import pytest

from check_release_distribution import exercise_installer


IGNORES_SHA = b"""#!/bin/sh
set -eu
curl -fsSL https://example.invalid/archive.tar.gz | tar -xz --strip-components=1
python3 scripts/install_ai_cockpit.py "$@"
"""

ENFORCES_SHA = b"""#!/bin/sh
set -eu
archive=source.tar.gz
curl -fsSL https://example.invalid/archive.tar.gz -o "$archive"
actual=$(sha256sum "$archive" | awk '{print $1}')
if [ "$actual" != "$AI_COCKPIT_TEMPLATE_SHA256" ]; then
  echo 'ERROR: archive SHA256 mismatch' >&2
  exit 2
fi
"""


@pytest.mark.parametrize(
    ("script", "supported"),
    [(IGNORES_SHA, False), (ENFORCES_SHA, True)],
)
def test_exercise_installer_matches_declared_capability(script, supported):
    exercise_installer(script, tag="v-test", sha256_supported=supported)


def test_exercise_installer_rejects_capability_drift():
    with pytest.raises(RuntimeError, match="disagrees with release.json"):
        exercise_installer(IGNORES_SHA, tag="v-test", sha256_supported=True)
