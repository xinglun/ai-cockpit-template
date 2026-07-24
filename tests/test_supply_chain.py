import json
import subprocess
import sys
from pathlib import Path

import check_supply_chain


ROOT = Path(__file__).resolve().parents[1]


def test_supply_chain_failure_log_does_not_include_issue_details(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["check_supply_chain.py", "secrets"])
    monkeypatch.setattr(
        check_supply_chain,
        "scan_secrets",
        lambda: ["secret.txt:github_token:1"],
    )

    assert check_supply_chain.main() == 1

    captured = capsys.readouterr()
    assert "secret.txt:github_token:1" not in captured.err
    assert "supply-chain check failed: 1 issue(s)" in captured.err


def test_secret_scanning_detects_github_token(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    token = "".join(["ghp_", "abcdefghijklmnopqrstuvwxyz1234567890", "\n"])
    (repo / "secrets.txt").write_text(token, encoding="utf-8")
    subprocess.run(["git", "add", "secrets.txt"], cwd=repo, check=True)
    monkeypatch.setattr(check_supply_chain, "ROOT", repo)

    assert check_supply_chain.scan_secrets() == ["secrets.txt:github_token:1"]


def test_secret_scanning_detects_untracked_github_token(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    token = "".join(["ghp_", "abcdefghijklmnopqrstuvwxyz1234567890", "\n"])
    (repo / "untracked.txt").write_text(token, encoding="utf-8")
    monkeypatch.setattr(check_supply_chain, "ROOT", repo)

    assert check_supply_chain.scan_secrets() == ["untracked.txt:github_token:1"]


def test_secret_scanning_ignores_ambient_git_repository_state(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    repo.mkdir()
    other.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "init", "-q"], cwd=other, check=True)
    token = "".join(["ghp_", "abcdefghijklmnopqrstuvwxyz1234567890", "\n"])
    (repo / "tracked.txt").write_text(token, encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    monkeypatch.setattr(check_supply_chain, "ROOT", repo)
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other / "index"))

    assert check_supply_chain.scan_secrets() == ["tracked.txt:github_token:1"]


def test_secret_scanning_ignores_binary_files(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    binary = repo / "image.png"
    binary.write_bytes(b"ghp_" + b"abcdefghijklmnopqrstuvwxyz1234567890")
    monkeypatch.setattr(check_supply_chain, "ROOT", repo)

    assert check_supply_chain.scan_secrets() == []


def test_secret_scanning_detects_truncated_private_key_material(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    fragment = "".join(["-----", "BEGIN PRIVATE KEY", "-----\n", "abc\n"])
    (repo / "key.txt").write_text(fragment, encoding="utf-8")
    monkeypatch.setattr(check_supply_chain, "ROOT", repo)

    assert check_supply_chain.scan_secrets() == ["key.txt:private_key_fragment:1"]


def test_secret_scanning_keeps_private_key_fixture_exemption(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    fixture = repo / "tests" / "test_core_gates.py"
    fixture.parent.mkdir(parents=True)
    fixture.write_text(
        "".join(
            [
                "-----",
                "BEGIN PRIVATE KEY",
                "-----\n",
                "abc\n",
                "-----",
                "END PRIVATE KEY",
                "-----\n",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "tests/test_core_gates.py"], cwd=repo, check=True)
    monkeypatch.setattr(check_supply_chain, "ROOT", repo)

    assert check_supply_chain.scan_secrets() == []


def test_dependency_vulnerability_scan_parses_pip_audit_output(monkeypatch):
    payload = {
        "dependencies": [
            {
                "name": "demo",
                "version": "1.0.0",
                "vulns": [{"id": "CVE-2024-0001", "fix_versions": ["1.0.1"]}],
            }
        ]
    }

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["python3", "-m", "pip_audit"],
            returncode=1,
            stdout=json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr(check_supply_chain.subprocess, "run", fake_run)
    monkeypatch.setattr(
        check_supply_chain,
        "build_sbom",
        lambda: {
            "components": [
                {
                    "type": "library",
                    "name": "demo",
                    "version": "1.0.0",
                    "purl": "pkg:pypi/demo@1.0.0",
                    "bom-ref": "pkg:pypi/demo@1.0.0",
                }
            ]
        },
    )

    assert check_supply_chain.scan_vulnerabilities() == [
        "pkg:pypi/demo@1.0.0:CVE-2024-0001 fix=1.0.1"
    ]


def test_workflow_action_discovery_includes_list_item_uses(tmp_path, monkeypatch):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        """
name: CI
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
      - run: python -m pytest
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_supply_chain, "WORKFLOW_DIR", workflows)

    assert check_supply_chain.parse_workflow_actions(workflows) == [
        {"type": "action", "name": "actions/checkout", "version": "v4"},
        {"type": "action", "name": "actions/setup-python", "version": "v5"},
    ]


def test_supply_chain_compare_or_write_reports_drift(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    baseline = repo / "sbom.json"
    monkeypatch.setattr(check_supply_chain, "ROOT", repo)

    assert check_supply_chain.compare_or_write(baseline, {"kind": "expected"}, write=True) == []
    assert check_supply_chain.compare_or_write(baseline, {"kind": "different"}, write=False) == [
        "sbom.json differs from the computed supply-chain evidence"
    ]


def test_supply_chain_uses_release_tag_commit_not_head(monkeypatch):
    commands = []
    seen_envs = []
    monkeypatch.setenv("GIT_DIR", "/tmp/ambient.git")
    monkeypatch.setenv("GIT_WORK_TREE", "/tmp/ambient")
    monkeypatch.setenv("AI_BASE_COMMIT", "f" * 40)
    monkeypatch.setattr(check_supply_chain, "PROVENANCE_BASELINE", Path("/missing/provenance.json"))

    tag = "v0.5.29"
    monkeypatch.setattr(check_supply_chain, "release_tag", lambda: tag)

    def fake_run(command, *, cwd, env, text, capture_output, check):
        commands.append(command)
        seen_envs.append(env)
        if command == ["git", "rev-parse", f"{tag}^{{commit}}"]:
            return subprocess.CompletedProcess(
                command, 0, stdout="eee1d4ad835a1d33cb70f26103536f77b593d2ce\n", stderr=""
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(check_supply_chain.subprocess, "run", fake_run)

    sbom = check_supply_chain.build_sbom()
    provenance = check_supply_chain.build_provenance(sbom)

    assert sbom["metadata"]["component"]["version"] == "eee1d4ad835a1d33cb70f26103536f77b593d2ce"
    assert provenance["commitSha"] == "eee1d4ad835a1d33cb70f26103536f77b593d2ce"
    assert commands == [
        ["git", "rev-parse", f"{tag}^{{commit}}"],
        ["git", "rev-parse", f"{tag}^{{commit}}"],
    ]
    assert len(seen_envs) == 2
    for env in seen_envs:
        assert env is not None
        assert "GIT_DIR" not in env
        assert "GIT_WORK_TREE" not in env
        assert "AI_BASE_COMMIT" not in env


def test_supply_chain_falls_back_to_checked_out_head_when_release_tag_is_absent(monkeypatch):
    monkeypatch.setattr(check_supply_chain, "release_tag", lambda: "v0.5.29")
    calls = []

    def fake_run(command, *, cwd, env, text, capture_output, check):
        calls.append(command)
        if command == ["git", "rev-parse", "v0.5.29^{commit}"]:
            return subprocess.CompletedProcess(command, 128, stdout="", stderr="missing tag")
        if command == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, stdout="head-source\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(check_supply_chain.subprocess, "run", fake_run)
    assert check_supply_chain.source_commit_sha() == "head-source"
    assert calls == [["git", "rev-parse", "v0.5.29^{commit}"], ["git", "rev-parse", "HEAD"]]


def test_supply_chain_reuses_candidate_baseline_for_next_patch_preparation(monkeypatch):
    monkeypatch.setattr(check_supply_chain, "release_tag", lambda: "v0.5.34")
    monkeypatch.setattr(
        check_supply_chain,
        "load_json",
        lambda path: (
            {
                "releaseState": "candidate",
                "published": False,
                "releaseTag": "v0.5.35",
                "basedOnReleaseTag": "v0.5.34",
            }
            if path.name == "next-release.json"
            else {"releaseTag": "v0.5.34", "commitSha": "baseline-source"}
        ),
    )
    calls = []

    def fake_run(command, *, cwd, env, text, capture_output, check):
        calls.append(command)
        if command == ["git", "rev-parse", "v0.5.34^{commit}"]:
            return subprocess.CompletedProcess(command, 128, stdout="", stderr="missing tag")
        if command == ["git", "rev-parse", "baseline-source"]:
            return subprocess.CompletedProcess(command, 0, stdout="baseline-source\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(check_supply_chain.subprocess, "run", fake_run)
    assert check_supply_chain.source_commit_sha() == "baseline-source"
    assert calls == [
        ["git", "rev-parse", "v0.5.34^{commit}"],
        ["git", "rev-parse", "baseline-source"],
    ]


def test_supply_chain_prefers_finalized_candidate_identity(monkeypatch):
    monkeypatch.setattr(check_supply_chain, "release_tag", lambda: "v0.5.39")
    monkeypatch.setattr(
        check_supply_chain,
        "load_json",
        lambda path: (
            {
                "format": "ai-cockpit-release-digests",
                "sourceCommit": "finalized-source",
                "tagTarget": "finalized-source",
                "metadataCommit": "finalized-source",
                "releaseTag": "v0.5.39",
            }
            if path.name == "release-digests.json"
            else {"releaseState": "candidate", "published": False}
        ),
    )
    calls = []

    def fake_run(command, *, cwd, env, text, capture_output, check):
        calls.append(command)
        if command == ["git", "rev-parse", "v0.5.39^{commit}"]:
            return subprocess.CompletedProcess(command, 128, stdout="", stderr="missing tag")
        if command == ["git", "rev-parse", "finalized-source"]:
            return subprocess.CompletedProcess(command, 0, stdout="finalized-source\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(check_supply_chain.subprocess, "run", fake_run)
    assert check_supply_chain.source_commit_sha() == "finalized-source"
    assert calls == [
        ["git", "rev-parse", "v0.5.39^{commit}"],
        ["git", "rev-parse", "finalized-source"],
    ]


def test_supply_chain_does_not_reuse_recorded_provenance_source(tmp_path, monkeypatch):
    provenance = tmp_path / "provenance.json"
    provenance.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        check_supply_chain,
        "PROVENANCE_BASELINE",
        provenance,
    )
    monkeypatch.setattr(
        check_supply_chain,
        "load_json",
        lambda _path: {"commitSha": "recorded-source"},
    )
    monkeypatch.setattr(check_supply_chain, "release_tag", lambda: "v0.5.28")
    calls = []

    def fake_run(command, *, cwd, env, text, capture_output, check):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="release-source\n", stderr="")

    monkeypatch.setattr(check_supply_chain.subprocess, "run", fake_run)

    assert check_supply_chain.source_commit_sha() == "release-source"
    assert calls == [["git", "rev-parse", "v0.5.28^{commit}"]]


def test_supply_chain_accepts_explicit_source_commit(monkeypatch):
    calls = []

    def fake_run(command, *, cwd, env, text, capture_output, check):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="source-commit\n", stderr="")

    monkeypatch.setattr(check_supply_chain.subprocess, "run", fake_run)
    assert check_supply_chain.source_commit_sha("source-ref") == "source-commit"
    assert calls == [["git", "rev-parse", "source-ref^{commit}"]]


def test_release_assets_write_source_bound_evidence_outside_baselines(tmp_path, monkeypatch):
    source = "a" * 40
    sbom = {"bomFormat": "CycloneDX", "metadata": {"component": {"version": source}}}
    provenance = {"commitSha": source, "releaseTag": "v0.5.28"}
    digests = {
        "format": "ai-cockpit-release-digests",
        "sourceCommit": source,
        "releaseTag": "v0.5.28",
        "artifacts": {},
    }
    monkeypatch.setattr(check_supply_chain, "source_commit_sha", lambda _value: source)
    monkeypatch.setattr(check_supply_chain, "build_sbom", lambda _value: sbom)
    monkeypatch.setattr(check_supply_chain, "build_provenance", lambda _sbom, _value: provenance)
    monkeypatch.setattr(
        check_supply_chain, "build_release_digests", lambda _sbom, _provenance: digests
    )

    output_dir = tmp_path / "evidence"
    check_supply_chain.write_release_assets(output_dir, "source-ref")
    assert json.loads((output_dir / "sbom.json").read_text(encoding="utf-8")) == sbom
    assert json.loads((output_dir / "provenance.json").read_text(encoding="utf-8")) == provenance
    assert json.loads((output_dir / "release-digests.json").read_text(encoding="utf-8")) == digests


def test_sbom_reports_generated_direct_transitive_and_hash_coverage(tmp_path, monkeypatch):
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "demo==1.0 \\\n    --hash=sha256:abc\n"
        "    # via -r requirements-dev.in\n"
        "transitive==2.0 \\\n    --hash=sha256:def\n"
        "    # via demo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_supply_chain, "LOCK_FILE", lock)
    monkeypatch.setattr(check_supply_chain, "WORKFLOW_DIR", tmp_path)
    monkeypatch.setattr(check_supply_chain, "source_commit_sha", lambda _=None: "source")

    coverage = check_supply_chain.build_sbom()["metadata"]["supplyChainCoverage"]
    assert coverage["workflowActions"] == 0
    assert coverage["lockedDirectDependencies"] == 1
    assert coverage["lockedDependencies"] == 2
    assert coverage["lockSemantics"]["transitiveDependencies"] == {
        "status": "generated",
        "count": 1,
        "source": "requirements-dev.lock",
    }
    assert coverage["lockSemantics"]["hashPins"] is True
    assert coverage["lockSemantics"]["requireHashesCompatible"] is True


def test_lock_semantics_fails_closed_when_a_package_has_no_hash(tmp_path):
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "demo==1.0 \\\n    --hash=sha256:abc\n"
        "    # via -r requirements-dev.in\n"
        "missing-hash==2.0\n"
        "    # via demo\n",
        encoding="utf-8",
    )

    semantics = check_supply_chain.lock_semantics(lock)

    assert semantics["hashPins"] is False
    assert semantics["requireHashesCompatible"] is False


def test_supply_chain_baselines_match_repository_state():
    assert (
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_supply_chain.py"), "sbom"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def test_repository_uses_in_and_lock_without_redundant_txt():
    assert (ROOT / "requirements-dev.in").is_file()
    assert (ROOT / "requirements-dev.lock").is_file()
    assert not (ROOT / "requirements-dev.txt").exists()
    assert (
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_supply_chain.py"), "provenance"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    assert (
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_supply_chain.py"), "secrets"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def test_parse_requirements_lock_removes_continuation_and_preserves_hashes(tmp_path):
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "demo-package==1.0.0 \\\n    --hash=sha256:abc123 \\\n    --hash=sha256:def456\n"
        "    # via -r requirements-dev.in\n"
        "    # via parent-package\n",
        encoding="utf-8",
    )

    assert check_supply_chain.parse_requirements_lock(lock) == [
        {
            "type": "library",
            "name": "demo-package",
            "version": "1.0.0",
            "hashes": ["abc123", "def456"],
            "via": ["-r requirements-dev.in", "parent-package"],
        }
    ]


def test_parse_requirements_lock_preserves_multiline_via_block(tmp_path):
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "root-package==1.0.0 \\\n+    --hash=sha256:abc123\n"
        "    # via\n"
        "    #   -r requirements-dev.in\n"
        "    #   parent-package\n",
        encoding="utf-8",
    )

    parsed = check_supply_chain.parse_requirements_lock(lock)

    assert parsed[0]["via"] == ["-r requirements-dev.in", "parent-package"]


def test_sbom_uses_cyclonedx_identity_and_dependency_metadata(tmp_path, monkeypatch):
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "root-package==1.0.0 \\\n    --hash=sha256:abc123\n"
        "    # via -r requirements-dev.in\n"
        "child-package==2.0.0 \\\n    --hash=sha256:def456\n"
        "    # via root-package\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_supply_chain, "LOCK_FILE", lock)
    monkeypatch.setattr(check_supply_chain, "WORKFLOW_DIR", tmp_path / "workflows")
    monkeypatch.setattr(check_supply_chain, "source_commit_sha", lambda _=None: "source")

    sbom = check_supply_chain.build_sbom()
    assert sbom["specVersion"] == "1.5"
    assert sbom["serialNumber"].startswith("urn:uuid:")
    assert sbom["metadata"]["timestamp"]
    assert sbom["metadata"]["tools"]
    assert sbom["metadata"]["tools"][0]["name"] == "check_supply_chain"
    assert sbom["metadata"]["tools"][0]["version"] == "source"
    components = {component["name"]: component for component in sbom["components"]}
    assert components["root-package"]["version"] == "1.0.0"
    assert components["root-package"]["purl"] == "pkg:pypi/root-package@1.0.0"
    assert components["root-package"]["bom-ref"] == "pkg:pypi/root-package@1.0.0"
    assert components["root-package"]["hashes"] == [{"alg": "SHA-256", "content": "abc123"}]
    dependencies = {
        dependency["ref"]: dependency.get("dependsOn", []) for dependency in sbom["dependencies"]
    }
    assert dependencies["ai-cockpit-template"] == ["pkg:pypi/root-package@1.0.0"]
    assert dependencies["pkg:pypi/root-package@1.0.0"] == ["pkg:pypi/child-package@2.0.0"]


def test_vulnerability_results_are_mapped_to_sbom_bom_refs():
    sbom = {
        "components": [
            {
                "type": "library",
                "name": "demo-package",
                "version": "1.0.0",
                "purl": "pkg:pypi/demo-package@1.0.0",
                "bom-ref": "pkg:pypi/demo-package@1.0.0",
            }
        ]
    }
    payload = {
        "dependencies": [
            {
                "name": "Demo_Package",
                "version": "1.0.0",
                "vulns": [{"id": "CVE-2024-0001", "fix_versions": ["1.0.1"]}],
            }
        ]
    }

    assert check_supply_chain.map_vulnerabilities_to_sbom(payload, sbom) == [
        "pkg:pypi/demo-package@1.0.0:CVE-2024-0001 fix=1.0.1"
    ]


def test_vulnerability_mapping_fails_closed_for_unknown_component():
    payload = {
        "dependencies": [{"name": "unknown", "version": "9.9.9", "vulns": [{"id": "CVE-1"}]}]
    }

    try:
        check_supply_chain.map_vulnerabilities_to_sbom(payload, {"components": []})
    except ValueError as exc:
        assert "cannot be mapped to SBOM component" in str(exc)
    else:
        raise AssertionError("unmapped vulnerability must fail closed")


def test_release_digest_manifest_covers_generated_evidence(tmp_path, monkeypatch):
    lock = tmp_path / "requirements.lock"
    installer = tmp_path / "install.sh"
    release = tmp_path / "release.json"
    lock.write_text("lock\n", encoding="utf-8")
    installer.write_text("installer\n", encoding="utf-8")
    release.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(check_supply_chain, "LOCK_FILE", lock)
    monkeypatch.setattr(check_supply_chain, "INSTALLER", installer)
    monkeypatch.setattr(check_supply_chain, "RELEASE_JSON", release)

    manifest = check_supply_chain.build_release_digests(
        {"bomFormat": "CycloneDX"}, {"commitSha": "source", "releaseTag": "v1"}
    )

    assert manifest["format"] == "ai-cockpit-release-digests"
    assert manifest["sourceCommit"] == "source"
    assert manifest["tagTarget"] == "source"
    assert manifest["metadataCommit"] == "source"
    assert set(manifest["artifacts"]) == {
        "requirements-dev.lock",
        ".ai/cockpit/sbom.json",
        ".ai/cockpit/provenance.json",
        "install.sh",
        "release.json",
    }
    assert manifest["artifacts"]["requirements-dev.lock"] == check_supply_chain.sha256_text(
        "lock\n"
    )


def test_release_digest_identity_fields_are_checked_against_candidate_baseline(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    cockpit = repo / ".ai" / "cockpit"
    lock = repo / "requirements-dev.lock"
    installer = repo / "install.sh"
    release = repo / "release.json"
    lock.parent.mkdir()
    lock.write_text("lock\n", encoding="utf-8")
    installer.write_text("installer\n", encoding="utf-8")
    release.write_text('{"releaseTag":"v1"}\n', encoding="utf-8")
    monkeypatch.setattr(check_supply_chain, "ROOT", repo)
    monkeypatch.setattr(check_supply_chain, "LOCK_FILE", lock)
    monkeypatch.setattr(check_supply_chain, "INSTALLER", installer)
    monkeypatch.setattr(check_supply_chain, "RELEASE_JSON", release)

    sbom = {"bomFormat": "CycloneDX"}
    provenance = {"commitSha": "source", "releaseTag": "v1"}
    manifest = check_supply_chain.build_release_digests(sbom, provenance)
    path = cockpit / "release-digests.json"
    assert check_supply_chain.compare_or_write(path, manifest, write=True) == []
    assert check_supply_chain.compare_or_write(path, manifest, write=False) == []

    stale = dict(manifest)
    stale["metadataCommit"] = "different-source"
    assert check_supply_chain.compare_or_write(path, stale, write=False) == [
        ".ai/cockpit/release-digests.json differs from the computed supply-chain evidence"
    ]


def test_release_evidence_reports_drift_when_generated_sbom_changes(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    cockpit = repo / ".ai" / "cockpit"
    lock = repo / "requirements-dev.lock"
    installer = repo / "install.sh"
    release = repo / "release.json"
    sbom_path = cockpit / "sbom.json"
    provenance_path = cockpit / "provenance.json"
    manifest_path = cockpit / "release-digests.json"
    lock.parent.mkdir()
    lock.write_text("lock\n", encoding="utf-8")
    installer.write_text("installer\n", encoding="utf-8")
    release.write_text('{"releaseTag":"v1"}\n', encoding="utf-8")
    monkeypatch.setattr(check_supply_chain, "ROOT", repo)
    monkeypatch.setattr(check_supply_chain, "LOCK_FILE", lock)
    monkeypatch.setattr(check_supply_chain, "INSTALLER", installer)
    monkeypatch.setattr(check_supply_chain, "RELEASE_JSON", release)

    sbom = {"bomFormat": "CycloneDX", "marker": "original"}
    provenance = {"commitSha": "source", "releaseTag": "v1"}
    manifest = check_supply_chain.build_release_digests(sbom, provenance)
    assert check_supply_chain.compare_or_write(sbom_path, sbom, write=True) == []
    assert check_supply_chain.compare_or_write(provenance_path, provenance, write=True) == []
    assert check_supply_chain.compare_or_write(manifest_path, manifest, write=True) == []

    sbom_path.write_text('{"bomFormat":"CycloneDX","marker":"changed"}\n', encoding="utf-8")

    assert check_supply_chain.compare_or_write(sbom_path, sbom, write=False) == [
        ".ai/cockpit/sbom.json differs from the computed supply-chain evidence"
    ]
