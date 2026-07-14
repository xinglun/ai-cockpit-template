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


def test_release_documentation_requires_one_verified_commit():
    documentation = (ROOT / "docs" / "reference" / "distribution.md").read_text(encoding="utf-8")

    assert "Both `smoke` and `compatibility`" in documentation
    assert "historical `v0.5.24` tag is immutable" in documentation
    assert "Maintainers dispatch `.github/workflows/release.yml`" in documentation
    assert "release.json.releaseTag" in documentation


def test_release_workflow_is_exact_sha_and_action_dependency_free():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "source_commit:" in workflow
    assert '[[ "$SOURCE_COMMIT" == "$GITHUB_SHA" ]]' in workflow
    assert "smoke.yml" in workflow and "compatibility.yml" in workflow
    assert "gh release create" in workflow
    assert "actions/checkout" not in workflow
