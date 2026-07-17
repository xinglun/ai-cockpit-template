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
    candidate_release_issues,
    release_claims,
    supply_chain_issues,
)
from ai_common import discover_remote_default_candidates, remote_default_branch_from_symref


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def test_release_distribution_uses_canonical_public_repository_by_default():
    assert release_distribution.PUBLIC_REPOSITORY == (
        "https://github.com/spirex-ds-dev/ai-cockpit-template.git"
    )


def test_release_metadata_declares_release_asset_authority():
    metadata = json.loads(release_distribution.RELEASE.read_text(encoding="utf-8"))

    assert metadata["releaseEvidenceAuthority"] == "release-assets-v1"


def test_candidate_release_is_next_patch_and_separate_from_published_metadata():
    published = json.loads((release_distribution.ROOT / "release.json").read_text(encoding="utf-8"))
    candidate = json.loads(
        (release_distribution.ROOT / "next-release.json").read_text(encoding="utf-8")
    )

    assert candidate_release_issues(candidate, published) == []
    assert candidate["releaseTag"] == published["releaseTag"] or candidate["releaseTag"].startswith(
        "v"
    )
    assert candidate["published"] is False


def test_remote_default_branch_candidates_require_explicit_remote_head():
    def run(args):
        if args == ["remote"]:
            return SimpleNamespace(returncode=0, stdout="origin\nupstream\n")
        if args == ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"]:
            return SimpleNamespace(returncode=0, stdout="origin/main\n")
        return SimpleNamespace(returncode=1, stdout="")

    assert discover_remote_default_candidates(run) == [("origin", "main")]
    assert remote_default_branch_from_symref("ref: refs/heads/main\tHEAD\n", "origin") == "main"
    assert remote_default_branch_from_symref("", "origin") is None


def test_release_source_binding_accepts_default_branch_head_and_evidence():
    assert (
        release_distribution.release_source_identity_issues(
            source_commit="default-sha",
            remote="origin",
            default_branch="main",
            default_branch_commit="default-sha",
            run_id="123",
        )
        == []
    )


def test_release_source_binding_rejects_feature_branch_source():
    issues = release_distribution.release_source_identity_issues(
        source_commit="feature-sha",
        remote="origin",
        default_branch="main",
        default_branch_commit="default-sha",
        run_id="123",
    )
    assert any("default branch" in issue for issue in issues)


def test_release_source_binding_fails_closed_without_remote_head():
    issues = release_distribution.release_source_identity_issues(
        source_commit="source-sha",
        remote="",
        default_branch="",
        default_branch_commit="",
        run_id="123",
    )
    assert "release remote is missing" in issues
    assert "release default branch is missing" in issues
    assert "remote default branch commit is missing" in issues


def test_release_source_evidence_requires_all_identity_fields():
    issues = release_distribution.release_source_identity_issues(
        source_commit="source-sha",
        remote="origin",
        default_branch="main",
        default_branch_commit="source-sha",
        run_id="",
    )
    assert "release run ID is missing" in issues


def test_supply_chain_issues_fail_closed_for_missing_mismatched_and_unscanned_evidence(
    tmp_path,
):
    metadata = {"supplyChain": {"requirementsLockDigest": "wrong", "secretScanning": False}}

    (tmp_path / "requirements-dev.lock").write_bytes(b"lock")
    issues = supply_chain_issues(metadata, root=tmp_path)

    joined = " ".join(issues)
    assert "sbomDigest is missing" in joined
    assert "provenanceDigest is missing" in joined
    assert "differs from requirements-dev.lock" in joined
    assert "secretScanning must be true" in joined


def test_release_claims_excludes_generated_supply_chain_digests():
    metadata = {
        "releaseTag": "v1.2.3",
        "publicContract": {"projectQualityTarget": "quality"},
        "capabilities": {"sha256ArchiveVerification": True},
        "supplyChain": {"sbomDigest": "stale"},
    }

    assert release_claims(metadata) == {
        "releaseTag": "v1.2.3",
        "publicContract": {"projectQualityTarget": "quality"},
        "capabilities": {"sha256ArchiveVerification": True},
    }


@pytest.mark.parametrize(
    "payload",
    [b"not-json", json.dumps(["not-an-object"]).encode(), json.dumps({"artifacts": []}).encode()],
)
def test_public_asset_integrity_rejects_invalid_manifest_shapes(tmp_path, payload):
    issues = release_distribution.public_release_asset_integrity_issues(
        tag="v1.2.3",
        tag_target="a" * 40,
        tag_root=tmp_path,
        assets={"release-digests.json": payload},
    )

    assert any("release-digests.json" in issue for issue in issues)


def test_public_asset_integrity_rejects_invalid_artifact_entries_and_bytes(tmp_path):
    (tmp_path / "release.json").write_bytes(b"release")
    manifest = {
        "format": "wrong",
        "version": 2,
        "sourceCommit": "wrong",
        "releaseTag": "wrong",
        "artifacts": {
            "release.json": "invalid",
            "missing.txt": "0" * 64,
            7: "0" * 64,
        },
    }
    manifest_bytes = json.dumps(manifest).encode()
    issues = release_distribution.public_release_asset_integrity_issues(
        tag="v1.2.3",
        tag_target="a" * 40,
        tag_root=tmp_path,
        assets={
            "sbom.json": b"downloaded",
            "provenance.json": b"downloaded",
            "release-digests.json": manifest_bytes,
        },
    )

    joined = " ".join(issues)
    assert "unsupported format" in joined
    assert "sourceCommit" in joined
    assert "invalid SHA-256" in joined
    assert "missing artifact in tag tree" in joined


def test_public_asset_integrity_allows_source_bound_candidate_baseline_differences(tmp_path):
    tree = tmp_path / ".ai" / "cockpit"
    tree.mkdir(parents=True)
    (tmp_path / "release.json").write_bytes(b"tree")
    (tree / "release-digests.json").write_bytes(b"tree-manifest")
    manifest = {
        "format": "release-digests-v1",
        "version": 1,
        "sourceCommit": "a" * 40,
        "releaseTag": "v1.2.3",
        "artifacts": {"release.json": "0" * 64},
    }
    issues = release_distribution.public_release_asset_integrity_issues(
        tag="v1.2.3",
        tag_target="a" * 40,
        tag_root=tmp_path,
        assets={
            "release-digests.json": json.dumps(manifest).encode(),
            "sbom.json": b"sbom",
            "provenance.json": b"prov",
        },
    )
    assert not any("bytes differ" in issue for issue in issues)


@pytest.mark.parametrize(
    "result",
    [
        SimpleNamespace(returncode=1, stderr="clone failed"),
        SimpleNamespace(returncode=0, stderr=""),
    ],
)
def test_inspect_tagged_release_fails_closed_before_release_metadata(monkeypatch, result):
    monkeypatch.setattr(release_distribution, "run_command", lambda *_args, **_kwargs: result)
    with pytest.raises(RuntimeError, match="clone|release.json"):
        release_distribution.inspect_tagged_release("v1.2.3")


def test_fetch_published_release_assets_downloads_all_required_assets(monkeypatch):
    release_payload = json.dumps(
        {
            "draft": False,
            "assets": [
                {"name": name, "browser_download_url": f"https://example.test/{name}"}
                for name in ("sbom.json", "provenance.json", "release-digests.json")
            ],
        }
    ).encode()

    def fake_urlopen(request, timeout):
        assert timeout == 30
        url = request.full_url
        if "/releases/tags/" in url:
            return _Response(release_payload)
        return _Response(url.rsplit("/", 1)[-1].encode())

    monkeypatch.setattr(release_distribution.urllib.request, "urlopen", fake_urlopen)

    assert release_distribution.fetch_published_release_assets("v1.2.3") == {
        "sbom.json": b"sbom.json",
        "provenance.json": b"provenance.json",
        "release-digests.json": b"release-digests.json",
    }


def test_fetch_published_release_assets_rejects_draft_and_missing_assets(monkeypatch):
    monkeypatch.setattr(
        release_distribution.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(json.dumps({"draft": True}).encode()),
    )
    with pytest.raises(RuntimeError, match="still draft"):
        release_distribution.fetch_published_release_assets("v1.2.3")


def test_fetch_published_release_assets_rejects_incomplete_published_release(monkeypatch):
    payload = {
        "draft": False,
        "assets": [
            {"name": "sbom.json", "browser_download_url": "https://example.test/sbom"},
            "malformed asset entry",
        ],
    }
    monkeypatch.setattr(
        release_distribution.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(json.dumps(payload).encode()),
    )
    with pytest.raises(RuntimeError, match="missing assets"):
        release_distribution.fetch_published_release_assets("v1.2.3")


def test_fetch_published_release_assets_rejects_missing_asset_list(monkeypatch):
    monkeypatch.setattr(
        release_distribution.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(json.dumps({"draft": False}).encode()),
    )
    with pytest.raises(RuntimeError, match="assets are missing"):
        release_distribution.fetch_published_release_assets("v1.2.3")


@pytest.mark.parametrize("payload", [[], {"draft": False, "assets": None}])
def test_fetch_published_release_assets_rejects_non_object_or_non_list(monkeypatch, payload):
    monkeypatch.setattr(
        release_distribution.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(json.dumps(payload).encode()),
    )
    with pytest.raises(RuntimeError):
        release_distribution.fetch_published_release_assets("v1.2.3")


def test_fetch_published_release_assets_uses_github_api(monkeypatch):
    assets = [
        {"name": name, "browser_download_url": f"https://example.test/{name}"}
        for name in ("sbom.json", "provenance.json", "release-digests.json")
    ]
    seen = []

    def fake_urlopen(request, timeout):
        seen.append(request.full_url)
        return _Response(
            json.dumps({"draft": False, "assets": assets}).encode() if len(seen) == 1 else b"data"
        )

    monkeypatch.setattr(release_distribution, "PUBLIC_REPOSITORY", "https://github.com/o/r.git")
    monkeypatch.setattr(release_distribution.urllib.request, "urlopen", fake_urlopen)
    release_distribution.fetch_published_release_assets("v1.2.3")
    assert seen[0] == "https://api.github.com/repos/o/r/releases/tags/v1.2.3"


def test_public_release_network_helpers_fail_closed_on_git_errors(monkeypatch):
    monkeypatch.setattr(
        release_distribution,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="", stderr="network down"),
    )
    with pytest.raises(RuntimeError, match="failed to list public tags"):
        release_distribution.list_remote_tags("https://example.test/repo.git")
    with pytest.raises(RuntimeError, match="failed to clone public release tag"):
        release_distribution.fetch_tagged_installer("v1.2.3")


def test_fetch_tagged_installer_rejects_clone_without_installer(monkeypatch, tmp_path):
    def fake_run(command, *, cwd, env):
        Path(command[-1]).mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(release_distribution, "run_command", fake_run)
    with pytest.raises(RuntimeError, match="missing install.sh"):
        release_distribution.fetch_tagged_installer("v1.2.3")


def test_public_release_network_helpers_return_verified_data(monkeypatch, tmp_path):
    def fake_run(command, *, cwd, env):
        if "ls-remote" in command:
            return SimpleNamespace(returncode=0, stdout="tag output", stderr="")
        install = Path(command[-1]) / "install.sh"
        install.parent.mkdir(parents=True, exist_ok=True)
        install.write_bytes(b"installer")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(release_distribution, "run_command", fake_run)
    assert release_distribution.list_remote_tags("https://example.test/repo.git") == "tag output"
    assert release_distribution.fetch_tagged_installer("v1.2.3") == b"installer"


def test_release_asset_identity_requires_one_tag_target_and_source_subject():
    provenance = {"commitSha": "source", "releaseTag": "v0.5.29"}
    digests = {
        "sourceCommit": "source",
        "releaseTag": "v0.5.29",
        "artifacts": {".ai/cockpit/sbom.json": "a", ".ai/cockpit/provenance.json": "b"},
        "correlation": {
            "workflowRunId": "123",
            "workflowRunSha": "source",
            "sourceCommit": "source",
            "releaseTag": "v0.5.29",
            "artifactDigests": {"sbom.json": "a", "provenance.json": "b"},
        },
    }

    assert (
        release_distribution.release_asset_identity_issues(
            tag="v0.5.29",
            tag_target="source",
            provenance=provenance,
            release_digests=digests,
        )
        == []
    )

    issues = release_distribution.release_asset_identity_issues(
        tag="v0.5.29",
        tag_target="tag-target",
        provenance={"commitSha": "wrong", "releaseTag": "v0.5.28"},
        release_digests={"sourceCommit": "other", "releaseTag": "v0.5.28"},
    )
    assert "tag target" in " ".join(issues)
    assert "provenance commitSha" in " ".join(issues)
    assert "release digest sourceCommit" in " ".join(issues)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("workflowRunId", "", "release correlation workflowRunId is missing"),
        ("workflowRunSha", "wrong", "release correlation workflowRunSha differs from tag target"),
        ("releaseTag", "v0.5.28", "release correlation releaseTag differs from tag"),
    ],
)
def test_release_correlation_rejects_missing_or_mismatched_identity(field, value, expected):
    correlation = {
        "workflowRunId": "123",
        "workflowRunSha": "source",
        "sourceCommit": "source",
        "releaseTag": "v0.5.29",
        "artifactDigests": {"sbom.json": "a", "provenance.json": "b"},
    }
    correlation[field] = value
    issues = release_distribution.release_asset_identity_issues(
        tag="v0.5.29",
        tag_target="source",
        provenance={"commitSha": "source", "releaseTag": "v0.5.29"},
        release_digests={
            "sourceCommit": "source",
            "releaseTag": "v0.5.29",
            "artifacts": {".ai/cockpit/sbom.json": "a", ".ai/cockpit/provenance.json": "b"},
            "correlation": correlation,
        },
    )
    assert expected in issues


def test_release_correlation_rejects_artifact_digest_mismatch():
    issues = release_distribution.release_asset_identity_issues(
        tag="v0.5.29",
        tag_target="source",
        provenance={"commitSha": "source", "releaseTag": "v0.5.29"},
        release_digests={
            "sourceCommit": "source",
            "releaseTag": "v0.5.29",
            "artifacts": {".ai/cockpit/sbom.json": "a", ".ai/cockpit/provenance.json": "b"},
            "correlation": {
                "workflowRunId": "123",
                "workflowRunSha": "source",
                "sourceCommit": "source",
                "releaseTag": "v0.5.29",
                "artifactDigests": {"sbom.json": "wrong", "provenance.json": "b"},
            },
        },
    )
    assert "release correlation artifact digest mismatch for sbom.json" in issues


def test_release_asset_identity_rejects_missing_subject_fields():
    issues = release_distribution.release_asset_identity_issues(
        tag="v0.5.29",
        tag_target="source",
        provenance={},
        release_digests={},
    )

    assert "provenance commitSha is missing" in issues
    assert "provenance releaseTag is missing" in issues
    assert "release digest sourceCommit is missing" in issues
    assert "release digest releaseTag is missing" in issues


def test_public_release_asset_integrity_binds_downloads_to_tag_tree(tmp_path):
    tree = tmp_path / "tree"
    (tree / ".ai" / "cockpit").mkdir(parents=True)
    files = {
        "requirements-dev.lock": b"lock",
        ".ai/cockpit/sbom.json": b"sbom",
        ".ai/cockpit/provenance.json": b"provenance",
        "install.sh": b"#!/bin/sh\nexit 0\n",
        "release.json": b'{"releaseTag":"v1.2.3"}\n',
    }
    for relative, payload in files.items():
        path = tree / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    manifest = {
        "format": "ai-cockpit-release-digests",
        "version": 1,
        "sourceCommit": "a" * 40,
        "releaseTag": "v1.2.3",
        "correlation": {
            "workflowRunId": "123",
            "workflowRunSha": "a" * 40,
            "sourceCommit": "a" * 40,
            "releaseTag": "v1.2.3",
            "artifactDigests": {
                "sbom.json": __import__("hashlib")
                .sha256(files[".ai/cockpit/sbom.json"])
                .hexdigest(),
                "provenance.json": __import__("hashlib")
                .sha256(files[".ai/cockpit/provenance.json"])
                .hexdigest(),
            },
        },
        "artifacts": {
            relative: __import__("hashlib").sha256(payload).hexdigest()
            for relative, payload in files.items()
        },
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True) + "\n").encode()
    (tree / ".ai/cockpit/release-digests.json").write_bytes(manifest_bytes)
    assets = {
        "sbom.json": files[".ai/cockpit/sbom.json"],
        "provenance.json": files[".ai/cockpit/provenance.json"],
        "release-digests.json": manifest_bytes,
    }

    assert (
        release_distribution.public_release_asset_integrity_issues(
            tag="v1.2.3",
            tag_target="a" * 40,
            tag_root=tree,
            assets=assets,
        )
        == []
    )


def test_public_release_asset_integrity_rejects_missing_and_altered_assets(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    manifest = {
        "format": "ai-cockpit-release-digests",
        "version": 1,
        "sourceCommit": "b" * 40,
        "releaseTag": "v1.2.3",
        "artifacts": {"release.json": "1" * 64},
    }
    manifest_bytes = (json.dumps(manifest) + "\n").encode()
    (tree / "release.json").write_bytes(b"release")

    issues = release_distribution.public_release_asset_integrity_issues(
        tag="v1.2.3",
        tag_target="c" * 40,
        tag_root=tree,
        assets={"release-digests.json": manifest_bytes, "sbom.json": b"tampered"},
    )

    joined = " ".join(issues)
    assert "sourceCommit" in joined
    assert "missing public asset: provenance.json" in joined
    assert "missing artifact in tag tree" not in joined
    assert "release.json" in joined


def test_public_release_asset_integrity_rejects_manifest_path_escape(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    manifest_bytes = json.dumps(
        {
            "format": "ai-cockpit-release-digests",
            "version": 1,
            "sourceCommit": "a" * 40,
            "releaseTag": "v1.2.3",
            "artifacts": {"../outside": "0" * 64},
        }
    ).encode()

    issues = release_distribution.public_release_asset_integrity_issues(
        tag="v1.2.3",
        tag_target="a" * 40,
        tag_root=tree,
        assets={"release-digests.json": manifest_bytes},
    )

    assert any("unsafe artifact path" in issue for issue in issues)


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
    error = capsys.readouterr().err
    assert (
        "tag release evidence is invalid" in error
        or "highest public tag" in error
        or "candidate metadata is invalid" in error
    )


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
    error = capsys.readouterr().err
    assert "tag release evidence is invalid" in error or "highest public tag" in error


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
