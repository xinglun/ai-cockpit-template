import importlib
import os
from types import SimpleNamespace

import pytest

import check_release_distribution as release_distribution
from check_release_distribution import exercise_installer, exercise_public_distribution, highest_semver_tag


IGNORES_SHA = b"""#!/bin/sh
set -eu
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git clone --depth 1 --branch "$AI_COCKPIT_TEMPLATE_REF" --single-branch https://example.invalid/ai-cockpit-template.git "$tmp/source"
python3 "$tmp/source/scripts/install_ai_cockpit.py" "$@"
"""

ENFORCES_SHA = b"""#!/bin/sh
set -eu
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git clone --depth 1 --branch "$AI_COCKPIT_TEMPLATE_REF" --single-branch https://example.invalid/ai-cockpit-template.git "$tmp/source"
archive="$tmp/source.tar.gz"
git -C "$tmp/source" archive --format=tar.gz --prefix=ai-cockpit/ HEAD -o "$archive"
actual=$(sha256sum "$archive" | awk '{print $1}')
if [ "$actual" != "$AI_COCKPIT_TEMPLATE_SHA256" ]; then
  echo 'ERROR: archive SHA256 mismatch' >&2
  exit 2
fi
python3 "$tmp/source/scripts/install_ai_cockpit.py" "$@"
"""

PUBLIC_CONTRACT_FIXTURE = b"""#!/bin/sh
set -eu
if [ "${GIT_DIR+x}" = x ] || [ "${GIT_WORK_TREE+x}" = x ]; then
  echo 'fixture received an explicit Git repository binding' >&2
  exit 12
fi
mkdir -p .ai/work-items/active
base=$(git rev-parse HEAD)
printf '{"baseCommit":"%s"}\n' "$base" > .ai/work-items/active/adopt_ai_cockpit.contract.json
cat > Makefile <<'EOF'
quality:
	@printf '%s\\n' 'ERROR: no project test command configured.' >&2; false
check-ai-adoption-ready:
	@printf '%s\\n' 'adoption readiness check failed' >&2; false
ai-finish:
	@true
check-ai-pr:
	@true
ai-start:
	@mkdir -p .ai/work-items/active
	@touch .ai/work-items/active/configure_ai_cockpit.contract.json
	@touch .ai/work-items/active/configure_ai_cockpit.summary.json
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


def test_exercise_public_distribution_ignores_hostile_ambient_git_environment(tmp_path, monkeypatch):
    parent_git = tmp_path / "parent.git"
    parent_git.mkdir()
    for key, value in {
        "GIT_DIR": str(parent_git),
        "GIT_WORK_TREE": str(tmp_path),
        "GIT_INDEX_FILE": str(tmp_path / "index"),
        "GIT_OBJECT_DIRECTORY": str(tmp_path / "objects"),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "alternates"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.bare",
        "GIT_CONFIG_VALUE_0": "true",
        "AI_BASE_COMMIT": "f" * 40,
    }.items():
        monkeypatch.setenv(key, value)

    exercise_public_distribution(PUBLIC_CONTRACT_FIXTURE, tag="v-test", quality_target="quality")
    assert os.environ["GIT_DIR"] == str(parent_git)
    assert os.environ["AI_BASE_COMMIT"] == "f" * 40


def test_exercise_public_distribution_rejects_missing_documented_target():
    with pytest.raises(RuntimeError, match="documented Make target is missing"):
        exercise_public_distribution(PUBLIC_CONTRACT_FIXTURE, tag="v-test", quality_target="ai-cockpit-quality")


def test_exercise_public_distribution_rejects_invalid_target():
    with pytest.raises(RuntimeError, match="invalid public quality target"):
        exercise_public_distribution(PUBLIC_CONTRACT_FIXTURE, tag="v-test", quality_target="--version")


def test_public_repository_override_is_honored(monkeypatch):
    monkeypatch.setenv("AI_COCKPIT_TEMPLATE_PUBLIC_REPOSITORY", "https://example.invalid/private.git")
    try:
        reloaded = importlib.reload(release_distribution)
        assert reloaded.PUBLIC_REPOSITORY == "https://example.invalid/private.git"
    finally:
        monkeypatch.delenv("AI_COCKPIT_TEMPLATE_PUBLIC_REPOSITORY", raising=False)
        importlib.reload(release_distribution)


def test_git_extraheader_args_uses_checkout_header(monkeypatch):
    def fake_run_command(command, *, cwd, env=None):
        if command == ["git", "config", "--get-all", "http.https://github.com/.extraheader"]:
            return SimpleNamespace(returncode=0, stdout="AUTHORIZATION: basic abc123\n")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(release_distribution, "run_command", fake_run_command)
    assert release_distribution.git_extraheader_args("https://github.com/xinglun/ai-cockpit-template.git") == [
        "-c",
        "http.https://github.com/.extraheader=AUTHORIZATION: basic abc123",
    ]


def test_git_extraheader_env_uses_checkout_header(monkeypatch):
    def fake_run_command(command, *, cwd, env=None):
        if command == ["git", "config", "--get-all", "http.https://github.com/.extraheader"]:
            return SimpleNamespace(returncode=0, stdout="AUTHORIZATION: basic abc123\n")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(release_distribution, "run_command", fake_run_command)
    assert release_distribution.git_extraheader_env("https://github.com/xinglun/ai-cockpit-template.git") == {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
        "GIT_CONFIG_VALUE_0": "AUTHORIZATION: basic abc123",
    }


def test_list_remote_tags_runs_outside_repo_root(monkeypatch):
    seen = {}

    def fake_run_command(command, *, cwd, env=None):
        seen["command"] = command
        seen["cwd"] = cwd
        if command == ["git", "config", "--get-all", "http.https://github.com/.extraheader"]:
            return SimpleNamespace(returncode=0, stdout="AUTHORIZATION: basic abc123\n", stderr="")
        if command[:3] == ["git", "-c", "http.https://github.com/.extraheader=AUTHORIZATION: basic abc123"] and command[3:6] == ["ls-remote", "--tags", "--refs"]:
            return SimpleNamespace(returncode=0, stdout="a refs/tags/v0.5.19\n", stderr="")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(release_distribution, "run_command", fake_run_command)
    assert release_distribution.list_remote_tags("https://github.com/xinglun/ai-cockpit-template.git") == "a refs/tags/v0.5.19\n"
    assert seen["cwd"] != release_distribution.ROOT
    assert seen["command"] != ["git", "config", "--get-all", "http.https://github.com/.extraheader"]


def test_highest_semver_tag_uses_numeric_version_order():
    refs = "\n".join([
        "a refs/tags/v0.5.9",
        "b refs/tags/v0.5.10",
        "c refs/tags/not-a-release",
    ])
    assert highest_semver_tag(refs) == "v0.5.10"


def test_highest_semver_tag_requires_release_tags():
    with pytest.raises(RuntimeError, match="no semantic-version tags"):
        highest_semver_tag("a refs/tags/latest")
