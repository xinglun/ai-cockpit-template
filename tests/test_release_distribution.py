import importlib
import os
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import check_release_distribution as release_distribution
from check_release_distribution import (
    exercise_installer,
    exercise_public_distribution,
    highest_semver_tag,
    is_next_patch_release,
)


def test_release_distribution_uses_canonical_public_repository_by_default():
    assert release_distribution.PUBLIC_REPOSITORY == (
        "https://github.com/spirex-ds-dev/ai-cockpit-template.git"
    )


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


def test_exercise_public_distribution_ignores_hostile_ambient_git_environment(
    tmp_path, monkeypatch
):
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


def test_release_network_commands_strip_ambient_git_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setenv("GIT_ASKPASS", "askpass")
    monkeypatch.setenv("SSH_ASKPASS", "ssh-askpass")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agent.sock")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/tmp/global.gitconfig")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/tmp/system.gitconfig")
    seen: list[tuple[list[str], dict[str, str] | None]] = []

    def fake_run_command(command, *, cwd, env=None):
        seen.append((command, env))
        if command[:5] == ["git", "-c", "credential.helper=", "-c", "http.extraHeader="]:
            if command[5] != "-c" or command[6] != "core.askPass=":
                raise AssertionError(f"unexpected git hardening prefix: {command!r}")
            if command[7] == "ls-remote":
                return SimpleNamespace(returncode=0, stdout="a refs/tags/v0.5.22\n", stderr="")
            if command[7] == "clone":
                repo = Path(command[-1])
                repo.mkdir(parents=True, exist_ok=True)
                (repo / "install.sh").parent.mkdir(parents=True, exist_ok=True)
                (repo / "install.sh").write_bytes(b"#!/bin/sh\nexit 0\n")
                return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(release_distribution, "run_command", fake_run_command)
    assert (
        release_distribution.list_remote_tags(
            "https://github.com/spirex-ds-dev/ai-cockpit-template.git"
        )
        == "a refs/tags/v0.5.22\n"
    )
    assert release_distribution.fetch_tagged_installer("v0.5.22") == b"#!/bin/sh\nexit 0\n"

    commands = [command for command, _env in seen]
    assert commands[0][:7] == [
        "git",
        "-c",
        "credential.helper=",
        "-c",
        "http.extraHeader=",
        "-c",
        "core.askPass=",
    ]
    assert commands[1][:7] == [
        "git",
        "-c",
        "credential.helper=",
        "-c",
        "http.extraHeader=",
        "-c",
        "core.askPass=",
    ]

    for _command, env in seen:
        assert env is not None
        assert env["GIT_CONFIG_NOSYSTEM"] == "1"
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GIT_CONFIG_GLOBAL"] == os.devnull
        assert env["GIT_CONFIG_SYSTEM"] == os.devnull
        for key in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS", "SSH_ASKPASS", "SSH_AUTH_SOCK"):
            assert key not in env


def test_release_preparation_evidence_matches_local_metadata():
    metadata = json.loads(release_distribution.RELEASE.read_text(encoding="utf-8"))
    issues = release_distribution.supply_chain_issues(metadata)

    assert issues == []


def test_release_distribution_fails_closed_on_supply_chain_drift(monkeypatch, tmp_path, capsys):
    release_json = tmp_path / "release.json"
    release_json.write_text(
        json.dumps(
            {
                "releaseTag": "v0.5.23",
                "publicContract": {"projectQualityTarget": "quality"},
                "capabilities": {"sha256ArchiveVerification": True},
                "supplyChain": {
                    "requirementsLockDigest": "0" * 64,
                    "sbomDigest": "0" * 64,
                    "provenanceDigest": "0" * 64,
                    "secretScanning": False,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(release_distribution, "RELEASE", release_json)

    monkeypatch.setattr(
        release_distribution,
        "list_remote_tags",
        lambda _repository: "a refs/tags/v0.5.23\n",
    )
    monkeypatch.setattr(
        release_distribution,
        "inspect_tagged_release",
        lambda _tag: (
            json.loads(release_json.read_text(encoding="utf-8")),
            b"",
            ["supplyChain drift"],
        ),
    )

    assert release_distribution.main() == 1
    assert "tag release evidence is invalid" in capsys.readouterr().err


def test_main_rejects_tag_missing_evidence_even_when_worktree_has_it(monkeypatch, capsys):
    metadata = json.loads(release_distribution.RELEASE.read_text(encoding="utf-8"))
    metadata["releaseTag"] = "v0.5.28"
    monkeypatch.setattr(
        release_distribution,
        "list_remote_tags",
        lambda _repository: "a refs/tags/v0.5.28\n",
    )
    monkeypatch.setattr(
        release_distribution,
        "inspect_tagged_release",
        lambda _tag: (
            metadata,
            b"#!/bin/sh\nexit 0\n",
            [
                "release.json supplyChain.provenanceDigest source file is missing: .ai/cockpit/provenance.json"
            ],
        ),
    )

    assert release_distribution.main() == 1
    assert "tag release evidence is invalid" in capsys.readouterr().err


def test_exercise_public_distribution_rejects_missing_documented_target():
    with pytest.raises(RuntimeError, match="documented Make target is missing"):
        exercise_public_distribution(
            PUBLIC_CONTRACT_FIXTURE, tag="v-test", quality_target="ai-cockpit-quality"
        )


def test_exercise_public_distribution_rejects_invalid_target():
    with pytest.raises(RuntimeError, match="invalid public quality target"):
        exercise_public_distribution(
            PUBLIC_CONTRACT_FIXTURE, tag="v-test", quality_target="--version"
        )


def test_public_repository_override_is_honored(monkeypatch):
    monkeypatch.setenv(
        "AI_COCKPIT_TEMPLATE_PUBLIC_REPOSITORY", "https://example.invalid/private.git"
    )
    try:
        reloaded = importlib.reload(release_distribution)
        assert reloaded.PUBLIC_REPOSITORY == "https://example.invalid/private.git"
    finally:
        monkeypatch.delenv("AI_COCKPIT_TEMPLATE_PUBLIC_REPOSITORY", raising=False)
        importlib.reload(release_distribution)


def test_release_preparation_accepts_only_next_patch_release():
    assert is_next_patch_release("v0.5.25", "v0.5.24")
    assert not is_next_patch_release("v0.6.0", "v0.5.24")
    assert not is_next_patch_release("v0.5.27", "v0.5.24")
    assert not is_next_patch_release("0.5.25", "v0.5.24")


def test_list_remote_tags_runs_outside_repo_root(monkeypatch):
    seen = {}

    def fake_run_command(command, *, cwd, env=None):
        seen["command"] = command
        seen["cwd"] = cwd
        if command[:7] == [
            "git",
            "-c",
            "credential.helper=",
            "-c",
            "http.extraHeader=",
            "-c",
            "core.askPass=",
        ]:
            if command[7:] == [
                "ls-remote",
                "--tags",
                "--refs",
                "https://github.com/spirex-ds-dev/ai-cockpit-template.git",
            ]:
                return SimpleNamespace(returncode=0, stdout="a refs/tags/v0.5.22\n", stderr="")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(release_distribution, "run_command", fake_run_command)
    assert (
        release_distribution.list_remote_tags(
            "https://github.com/spirex-ds-dev/ai-cockpit-template.git"
        )
        == "a refs/tags/v0.5.22\n"
    )
    assert seen["cwd"] != release_distribution.ROOT


def test_fetch_tagged_installer_uses_plain_git_without_checkout_auth(monkeypatch):
    seen = {}

    def fake_run_command(command, *, cwd, env=None):
        seen["command"] = command
        seen["cwd"] = cwd
        if command[:7] == [
            "git",
            "-c",
            "credential.helper=",
            "-c",
            "http.extraHeader=",
            "-c",
            "core.askPass=",
        ]:
            if command[7:] == [
                "clone",
                "--depth",
                "1",
                "--branch",
                "v0.5.22",
                "--single-branch",
                release_distribution.PUBLIC_REPOSITORY,
                str(cwd / "repo"),
            ]:
                installer = cwd / "repo" / "install.sh"
                installer.parent.mkdir(parents=True, exist_ok=True)
                installer.write_bytes(b"#!/bin/sh\nexit 0\n")
                source_root = release_distribution.ROOT
                (cwd / "repo" / "release.json").write_bytes(
                    (source_root / "release.json").read_bytes()
                )
                for source in release_distribution.SUPPLY_CHAIN_FILES.values():
                    target = cwd / "repo" / source.relative_to(source_root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read_bytes())
                return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(release_distribution, "run_command", fake_run_command)
    installer = release_distribution.fetch_tagged_installer("v0.5.22")
    assert installer == b"#!/bin/sh\nexit 0\n"
    assert seen["cwd"] != release_distribution.ROOT


def test_highest_semver_tag_uses_numeric_version_order():
    refs = "\n".join(
        [
            "a refs/tags/v0.5.9",
            "b refs/tags/v0.5.10",
            "c refs/tags/not-a-release",
        ]
    )
    assert highest_semver_tag(refs) == "v0.5.10"


def test_highest_semver_tag_requires_release_tags():
    with pytest.raises(RuntimeError, match="no semantic-version tags"):
        highest_semver_tag("a refs/tags/latest")
