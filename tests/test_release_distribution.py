import pytest

from check_release_distribution import exercise_installer, exercise_public_distribution


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

PUBLIC_CONTRACT_FIXTURE = b"""#!/bin/sh
set -eu
cat > Makefile <<'EOF'
quality:
	@printf '%s\\n' 'ERROR: no project test command configured.' >&2; false
check-ai-adoption-ready:
	@printf '%s\\n' 'adoption readiness check failed' >&2; false
ai-finish:
	@true
check-ai-pr:
	@true
EOF
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


def test_exercise_public_distribution_validates_documented_journey():
    exercise_public_distribution(PUBLIC_CONTRACT_FIXTURE, tag="v-test", quality_target="quality")


def test_exercise_public_distribution_rejects_missing_documented_target():
    with pytest.raises(RuntimeError, match="documented Make target is missing"):
        exercise_public_distribution(PUBLIC_CONTRACT_FIXTURE, tag="v-test", quality_target="ai-cockpit-quality")


def test_exercise_public_distribution_rejects_invalid_target():
    with pytest.raises(RuntimeError, match="invalid public quality target"):
        exercise_public_distribution(PUBLIC_CONTRACT_FIXTURE, tag="v-test", quality_target="--version")
