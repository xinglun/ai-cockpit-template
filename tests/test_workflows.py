from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_compatibility_runs_on_main_pushes_and_pull_requests():
    workflow = (ROOT / ".github" / "workflows" / "compatibility.yml").read_text(encoding="utf-8")

    assert "  push:\n    branches:\n      - main" in workflow
    assert "  pull_request:" in workflow
    assert "  workflow_dispatch:" in workflow
    assert "  compatibility-gate:" in workflow
    assert "needs:\n      - shellcheck" in workflow
    assert 'test "$result" = success' in workflow
    assert workflow.count("fetch-depth: 0") == 5
    assert "toolchain: stable" in workflow


def test_compatibility_separates_blocking_baseline_from_latest_probes():
    workflow = (ROOT / ".github" / "workflows" / "compatibility.yml").read_text(encoding="utf-8")
    gate = workflow.split("  compatibility-gate:", 1)[1].split("  compatibility-latest:", 1)[0]
    assert "needs:\n      - shellcheck\n      - python-platform-matrix" in gate
    assert "real-stack-quality" not in gate
    assert "compatibility-latest:" in workflow
    assert "continue-on-error: true" in workflow
    assert "Latest probes are exploratory evidence" in workflow


def test_release_documentation_requires_one_verified_commit():
    documentation = (ROOT / "docs" / "reference" / "distribution.md").read_text(encoding="utf-8")

    assert "Both `smoke` and `compatibility`" in documentation
    assert "historical release tag is immutable" in documentation
    assert "Maintainers dispatch `.github/workflows/release.yml`" in documentation
    assert "release.json.releaseTag" in documentation
    assert "pending publication" in documentation
    assert "strict smoke verification" in documentation


def test_release_workflow_is_exact_sha_and_action_dependency_free():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "source_commit:" in workflow
    assert "  actions: write" in workflow
    assert '[[ "$SOURCE_COMMIT" == "$GITHUB_SHA" ]]' in workflow
    assert "gh auth setup-git" in workflow
    assert 'git fetch --no-tags --quiet origin "${SOURCE_COMMIT}"' in workflow
    assert "smoke.yml" in workflow and "compatibility.yml" in workflow
    assert "deadline=$((SECONDS + 900))" in workflow
    assert 'any(.[]; .conclusion == "success")' in workflow
    assert 'any(.[]; .status != "completed")' in workflow
    assert "timed out waiting for ${workflow}" in workflow
    assert "sleep 15" in workflow
    assert "gh release create" in workflow
    assert "gh workflow run smoke.yml" in workflow
    assert "actions/checkout" not in workflow
    assert "release-assets" in workflow
    assert "'.commitSha'" in workflow
    assert "release-digests.json" in workflow
    assert "#sbom.json" in workflow
    assert "#provenance.json" in workflow


def test_smoke_preparation_mode_is_event_based_and_dispatch_stays_strict():
    workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")
    assert "github.event_name == 'pull_request'" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "startsWith(github.head_ref" not in workflow


def test_smoke_workflow_has_release_blocking_delegated_secret_scan():
    workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")
    assert "Delegated secret scanning (release-blocking)" in workflow
    assert "github.com/zricethezav/gitleaks/v8@9c72c5f9f05200fdc06e3f1b16e9aaa89fbe9f75" in workflow
    assert "fetch-depth: 0" in workflow
    assert 'gitleaks" detect --source="$GITHUB_WORKSPACE"' in workflow
