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
    assert workflow.count("fetch-depth: 0") == 7
    assert 'toolchain: "1.86.0"' in workflow


def test_compatibility_runs_lockfile_reproducibility_on_clean_runner():
    workflow = (ROOT / ".github" / "workflows" / "compatibility.yml").read_text(encoding="utf-8")
    lockfile = workflow.split("  lockfile-reproducibility:", 1)[1].split(
        "  real-stack-quality:", 1
    )[0]
    assert 'python-version: "3.10"' in lockfile
    assert (
        "python -m pip install --disable-pip-version-check pip-tools typing-extensions==4.16.0"
        in lockfile
    )
    assert "make check-lockfile-reproducibility" in lockfile


def test_compatibility_separates_blocking_baseline_from_latest_probes():
    workflow = (ROOT / ".github" / "workflows" / "compatibility.yml").read_text(encoding="utf-8")
    gate = workflow.split("  compatibility-gate:", 1)[1].split("  compatibility-latest:", 1)[0]
    assert "needs:" in gate
    assert "real-stack-quality" in gate
    assert "extended-real-stack-quality" in gate
    assert "mobile-stack-quality" in gate
    assert "compatibility-latest:" in workflow
    assert "continue-on-error: true" not in gate
    assert "fixed compatibility baseline is the blocking release gate" in workflow
    assert 'go-version: "1.24.4"' in workflow
    assert 'toolchain: "1.86.0"' in workflow
    assert 'node-version: "24.11.1"' in workflow


def test_latest_compatibility_probe_uses_distinct_current_tool_commands():
    workflow = (ROOT / ".github" / "workflows" / "compatibility.yml").read_text(encoding="utf-8")
    latest = workflow.split("  latest-ecosystem-probe:", 1)[1].split("  compatibility-gate:", 1)[0]
    report = workflow.split("  compatibility-latest:", 1)[1]
    assert "continue-on-error: true" in latest
    assert 'python-version: "3.x"' in latest
    assert "check-latest: true" in latest
    assert "go-version: stable" in latest
    assert "node-version: node" in latest
    assert "ruby-version: ruby-head" in latest
    assert "php-version: latest" in latest
    assert "brew install swift-format" in latest
    assert "needs:\n      - latest-ecosystem-probe" in report
    assert "fixed compatibility baseline is the blocking release gate" in report


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
    assert 'requested_source_commit="$SOURCE_COMMIT"' in workflow
    assert (
        "required: false"
        in workflow.split("      source_commit:", 1)[1].split("        type: string", 1)[0]
    )
    assert 'requested_source_commit="$SOURCE_COMMIT"' in workflow
    assert 'SOURCE_COMMIT="$DEFAULT_BRANCH_COMMIT"' in workflow
    assert "source_commit must equal the freshly resolved default branch commit" in workflow
    assert 'echo "SOURCE_COMMIT=$SOURCE_COMMIT"' in workflow
    assert "gh auth setup-git" in workflow
    assert 'git fetch --no-tags --quiet origin "${SOURCE_COMMIT}"' in workflow
    assert (
        'git fetch --no-tags --quiet origin "refs/tags/${RELEASE_TAG}:refs/tags/${RELEASE_TAG}"'
        in workflow
    )
    assert 'git rev-parse "$RELEASE_TAG^{commit}"' in workflow
    assert workflow.index(
        'git fetch --no-tags --quiet origin "refs/tags/${RELEASE_TAG}:refs/tags/${RELEASE_TAG}"'
    ) < workflow.index('git rev-parse "$RELEASE_TAG^{commit}"')
    assert "smoke.yml" in workflow and "compatibility.yml" in workflow
    assert "deadline=$((SECONDS + 900))" in workflow
    assert 'any(.[]; .conclusion == "success")' in workflow
    assert 'any(.[]; .status != "completed")' in workflow
    assert "timed out waiting for ${workflow}" in workflow
    assert "sleep 15" in workflow
    assert "gh release create" in workflow
    assert 'git push origin "$SOURCE_COMMIT:refs/tags/$RELEASE_TAG"' in workflow
    assert workflow.index(
        'git push origin "$SOURCE_COMMIT:refs/tags/$RELEASE_TAG"'
    ) < workflow.index("gh release create")
    assert "--draft" in workflow
    assert (
        'gh workflow run smoke.yml --repo "$GITHUB_REPOSITORY" --ref "$GITHUB_REF_NAME"' in workflow
    )
    assert 'gh release edit "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --draft=false' in workflow
    assert "actions/checkout" not in workflow
    assert "release-assets" in workflow
    assert "'.commitSha'" in workflow
    assert "release-digests.json" in workflow
    assert "evidenceBundleDigest" in workflow
    assert "EVIDENCE_BUNDLE_DIGEST" in workflow
    assert "#sbom.json" in workflow
    assert "#provenance.json" in workflow
    assert "git ls-remote --symref origin HEAD" in workflow
    assert "refs/remotes/origin/${RELEASE_DEFAULT_BRANCH}" in workflow
    assert 'requested_source_commit="$SOURCE_COMMIT"' in workflow
    assert "release-source.json" in workflow
    assert "RELEASE_REMOTE" in workflow
    assert "RELEASE_DEFAULT_BRANCH" in workflow
    assert "GITHUB_RUN_ID" in workflow


def test_release_workflow_publishes_provider_bundle_digest_in_source_evidence():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    bind = workflow.index("Bind the generated evidence bundle digest")
    draft = workflow.index("Create exact-SHA tag and Draft GitHub Release")
    assert workflow.index("release-source.with-digest.json", bind) < draft
    assert workflow.index(".evidenceBundleDigest", bind) < draft


def test_release_workflow_rejects_stale_source_before_mutations():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    mismatch = workflow.index("source_commit must equal the freshly resolved default branch commit")
    checkout = workflow.index('git checkout --detach --quiet "${SOURCE_COMMIT}"')
    evidence = workflow.index("Generate source-bound release evidence")
    tag = workflow.index('git push origin "$SOURCE_COMMIT:refs/tags/$RELEASE_TAG"')
    draft = workflow.index("gh release create")
    publish = workflow.index('gh release edit "$RELEASE_TAG"')
    assert mismatch < checkout < evidence < tag < draft < publish
    assert "rm " not in workflow
    assert "unlink" not in workflow


def test_release_workflow_runs_strict_smoke_before_tag_and_release_mutations():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    smoke = workflow.index("Dispatch strict smoke verification")
    tag = workflow.index("Create exact-SHA tag and Draft GitHub Release")
    publish = workflow.index("Publish verified Draft Release")
    assert smoke < tag < publish
    dispatch = workflow[smoke:tag]
    assert '--ref "$GITHUB_REF_NAME"' in dispatch
    assert '--commit "$SOURCE_COMMIT"' in dispatch


def test_release_workflow_requires_lockfile_reproducibility():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "Require reproducible dependency lockfile" in workflow
    assert "make check-lockfile-reproducibility" in workflow


def test_release_workflow_generates_and_verifies_correlation_record():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert '--workflow-run-id "$GITHUB_RUN_ID"' in workflow
    assert '--workflow-run-sha "$GITHUB_SHA"' in workflow
    assert "correlation.workflowRunId" in workflow
    assert "correlation.workflowRunSha" in workflow
    assert "correlation.sourceCommit" in workflow
    assert "correlation.releaseTag" in workflow
    assert workflow.index("Generate source-bound release evidence") < workflow.index(
        "Create exact-SHA tag and Draft GitHub Release"
    )


def test_smoke_preparation_mode_is_event_based_and_dispatch_stays_strict():
    workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")
    assert "github.event_name == 'pull_request'" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "startsWith(github.head_ref" not in workflow


def test_smoke_workflow_has_release_blocking_delegated_secret_scan():
    workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8")
    assert "Delegated secret scanning (release-blocking)" in workflow
    assert "github.com/zricethezav/gitleaks/v8@9c72c5f9f05200fdc06e3f1b16e9aaa89fbe9f75" in workflow
    assert "fetch-depth: 0" in workflow
    assert 'gitleaks" detect --source="$GITHUB_WORKSPACE"' in workflow
