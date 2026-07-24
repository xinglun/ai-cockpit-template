---
author: Ray
title: "Release Post-Merge Source Verification Implementation Plan"
description: Implement and close the candidate-to-merge release verification gap before v0.5.39.
keywords:
  - release
  - preflight
  - source-identity
  - work-item-lifecycle
---

# Release Post-Merge Source Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make premerge freeze evidence describe candidate content and make a real candidate-to-merge regression prove that the exact merged default-branch commit passes release preflight.

**Architecture:** Premerge finalization keeps `origin/main` as the future identity reference but hashes the clean candidate `HEAD`. Hosted preflight resolves `origin/main` after merge, recalculates the same canonical content from the detached merge commit, and emits exact identity through provider-owned `release-source.json`.

**Tech Stack:** Python 3 standard library, pytest, Git CLI, Make, JSON, Markdown.

## Global Constraints

- Do not create or move v0.5.39 until this Work Item is merged, closed, synchronized, and merged-main CI/preflight passes.
- Do not weaken exact-SHA, controlled-origin-ref, archive, lifecycle, or ownership validation.
- `archiveGrowth=538` and later counts remain warning-only under `enforcement.archiveGrowth: warning`.
- Final Markdown complexity must be at most 9550; retain this design/plan and repay their cost by compacting completed historical plans to archive-backed closure stubs.

---

### Task 1: Add a real candidate-to-merge regression

**Files:**
- Modify: `tests/test_release_preflight.py`

**Interfaces:**
- Consumes: `scripts/finalize_release_freeze.py`, `scripts/check_release_preflight.py`, and the Git CLI.
- Produces: `_build_candidate_merge(tmp_path) -> tuple[Path, Path, str]` and `_run_release_preflight(repo, source_ref) -> CompletedProcess[str]`.

- [ ] **Step 1: Add the fixture helpers**

Add `import shutil`, then add these helpers before the existing detached-repository test:

```python
def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _run_release_preflight(repo: Path, source_ref: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "check_release_preflight.py"),
            "--root",
            str(repo),
            "--source-commit",
            source_ref,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _build_candidate_merge(tmp_path: Path) -> tuple[Path, Path, str]:
    source_root = Path.cwd()
    repo = tmp_path / "source"
    remote = tmp_path / "origin.git"
    fresh = tmp_path / "fresh"
    repo.mkdir()
    for relative in (
        "ai_common.py",
        "finalize_release_freeze.py",
        "check_release_preflight.py",
        "release_archive.py",
    ):
        target = repo / "scripts" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / "scripts" / relative, target)
    (repo / "scripts" / "check_supply_chain.py").write_text(
        "import hashlib\n\n"
        "def sha256_text(value: str) -> str:\n"
        "    return hashlib.sha256(value.encode()).hexdigest()\n",
        encoding="utf-8",
    )
    (repo / ".gitattributes").write_text(
        "release.json export-ignore\n"
        "next-release.json export-ignore\n"
        "release-state.json export-ignore\n"
        ".ai/cockpit/release-digests.json export-ignore\n"
        ".ai/cockpit/release-freeze.json export-ignore\n"
        ".ai/work-items/archive export-ignore\n"
        ".ai/work-items/active export-ignore\n"
        ".ai/cockpit/current_status.md export-ignore\n",
        encoding="utf-8",
    )
    (repo / "source.txt").write_text("base\n", encoding="utf-8")
    (repo / ".ai" / "cockpit").mkdir(parents=True)
    (repo / ".ai" / "cockpit" / "current_status.md").write_text(
        "- State: `no_active_work_item`\n", encoding="utf-8"
    )
    _write_json(repo / ".ai" / "cockpit" / "release-freeze.json", {"state": "candidate"})
    _write_json(
        repo / ".ai" / "cockpit" / "release-digests.json",
        {"sourceCommit": "old", "artifacts": {}},
    )
    _write_json(
        repo / "release.json",
        {"releaseTag": "v0.5.39", "releaseArchive": {"sha256": "old"}},
    )
    _write_json(
        repo / "next-release.json",
        {"releaseTag": "v0.5.40", "basedOnReleaseTag": "v0.5.39"},
    )
    _write_json(
        repo / "release-state.json",
        {
            "state": "candidate_prepared",
            "releaseTag": "v0.5.40",
            "previousRelease": "v0.5.39",
            "metadataDigests": {"published": "old"},
        },
    )
    policy = repo / ".ai" / "guards" / "governance_complexity_policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        "max:\n  archiveGrowth: 538\nenforcement:\n  archiveGrowth: warning\n",
        encoding="utf-8",
    )
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Release Test")
    _git(repo, "config", "user.email", "release-test@example.invalid")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(
        ["git", "--git-dir", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"],
        check=True,
    )
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")
    _git(repo, "remote", "set-head", "origin", "main")
    _git(repo, "switch", "-q", "-c", "candidate")
    (repo / "source.txt").write_text("candidate\n", encoding="utf-8")
    contract = repo / ".ai" / "work-items" / "archive" / "2026" / "task.contract.json"
    _write_json(
        contract,
        {
            "scope": [
                "release.json",
                "release-state.json",
                ".ai/cockpit/release-freeze.json",
                ".ai/cockpit/release-digests.json",
            ]
        },
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "candidate")
    subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "finalize_release_freeze.py"),
            "--premerge-task",
            "task",
            "--source-commit",
            "origin/main",
            "--tag-target",
            "origin/main",
            "--metadata-commit",
            "origin/main",
        ],
        cwd=repo,
        check=True,
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "freeze candidate")
    _git(repo, "switch", "-q", "main")
    _git(repo, "merge", "-q", "--no-ff", "candidate", "-m", "merge candidate")
    merge_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "-q", "origin", "main")
    _git(fresh.parent, "init", "-q", str(fresh))
    _git(fresh, "remote", "add", "origin", str(remote))
    _git(fresh, "fetch", "-q", "origin", "main:refs/remotes/origin/main")
    _git(fresh, "checkout", "--detach", "-q", merge_commit)
    return repo, fresh, merge_commit
```

- [ ] **Step 2: Add the successful transition test and tighten the unit expectation**

```python
def test_candidate_freeze_survives_real_no_ff_merge_and_detached_preflight(tmp_path):
    _, fresh, merge_commit = _build_candidate_merge(tmp_path)
    result = _run_release_preflight(fresh, "origin/main")
    assert result.returncode == 0, result.stderr
    assert f"source={merge_commit}" in result.stdout
    assert "release preflight passed" in result.stdout
```

In `test_finalize_release_freeze_premerge_requires_archived_work_item`, change:

```python
assert materialized == [("tree", "old-commit"), ("archive", "old-commit")]
```

to:

```python
assert materialized == [("tree", "commit"), ("archive", "commit")]
```

- [ ] **Step 3: Run RED**

Run:

```bash
python3 -m pytest -q \
  tests/test_release_preflight.py::test_finalize_release_freeze_premerge_requires_archived_work_item \
  tests/test_release_preflight.py::test_candidate_freeze_survives_real_no_ff_merge_and_detached_preflight
```

Expected: both tests fail because the current finalizer passes old `origin/main` to the canonical builders.

### Task 2: Restore candidate content materialization

**Files:**
- Modify: `scripts/finalize_release_freeze.py`
- Test: `tests/test_release_preflight.py`

**Interfaces:**
- Consumes: concrete `resolved_head` plus symbolic `source_identity`.
- Produces: candidate-derived `sourceTree`/`archiveSha256` and unchanged controlled identity fields.

- [ ] **Step 1: Implement the minimal correction**

Replace the premerge `resolved_source` block with:

```python
# The controlled source identity remains a future default-branch ref for
# post-merge resolution. Canonical content is materialized from this clean
# candidate HEAD; export-ignored metadata and Work Item evidence let a clean
# merge preserve those bytes while changing commit identity.
materialization_commit = resolved_head if premerge_task is not None else source_identity
```

- [ ] **Step 2: Run GREEN**

Run the two-test command from Task 1. Expected: `2 passed`.

- [ ] **Step 3: Add fail-closed drift coverage**

```python
def test_postmerge_preflight_rejects_included_content_after_candidate_merge(tmp_path):
    repo, fresh, _ = _build_candidate_merge(tmp_path)
    (repo / "source.txt").write_text("post-merge drift\n", encoding="utf-8")
    _git(repo, "add", "source.txt")
    _git(repo, "commit", "-q", "-m", "drift after merge")
    drift_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "-q", "origin", "main")
    _git(fresh, "fetch", "-q", "origin", "main:refs/remotes/origin/main")
    _git(fresh, "checkout", "--detach", "-q", drift_commit)
    result = _run_release_preflight(fresh, "origin/main")
    assert result.returncode == 1
    assert "release preflight blocked" in result.stderr
    assert "archiveSha256 does not match regenerated archive" in result.stderr
```

- [ ] **Step 4: Pin archive warning coverage to the observed boundary**

Change the warning-only test to call:

```python
validate_release_preflight(
    **_fixture(archive_count=538, archive_max=200, archive_enforcement="warning")
)
```

Expected: an empty issue list.

- [ ] **Step 5: Run focused and full tests**

```bash
python3 -m pytest -q tests/test_release_preflight.py
python3 -m pytest -q
```

Expected: all tests pass with zero failures.

- [ ] **Step 6: Commit code and tests**

```bash
git add scripts/finalize_release_freeze.py tests/test_release_preflight.py
git commit -m "fix: verify candidate content across release merge"
```

### Task 3: Correct the release lifecycle documentation

**Files:**
- Modify: `docs/reference/distribution.md`
- Modify: `docs/reference/ai-cockpit-work-item-lifecycle.md`
- Modify: `docs/superpowers/plans/README.md`
- Replace with concise closure stubs: `docs/superpowers/plans/2026-07-22-project-calibration-recalibration.md`
- Replace with concise closure stubs: `docs/superpowers/plans/2026-07-22-installed-lifecycle-review-remediation.md`
- Replace with concise closure stubs: `docs/superpowers/plans/2026-07-22-ai-cockpit-governance-hardening.md`
- Delete: `docs/superpowers/plans/2026-07-24-release-preflight-merged-source-parity.md`

**Interfaces:**
- Consumes: the implemented candidate/materialized-content distinction.
- Produces: one unambiguous maintainer sequence and removes the plan that prescribed `old-commit`.

- [ ] **Step 1: Replace the incorrect lifecycle statement**

Document that premerge `sourceTree` and `archiveSha256` come from clean candidate `HEAD`; the controlled default-branch ref is retained only for post-merge identity resolution.

- [ ] **Step 2: Clarify the provider boundary**

Document that the hosted workflow resolves the exact merged SHA, checks it out detached, regenerates canonical content, emits `release-source.json`, and stops before tag mutation on mismatch.

- [ ] **Step 3: Remove the superseded contradictory plan**

Delete `docs/superpowers/plans/2026-07-24-release-preflight-merged-source-parity.md`, whose test instruction explicitly expects `old-commit`.

- [ ] **Step 4: Compact completed historical plans and fix retention**

Preserve each historical plan path and YAML metadata, but replace its completed
execution body with a closure stub that names the authoritative archived Work
Item evidence and states that no new Work Item may be launched from it. Update
the plan index so completed plans may be compacted only after reference scanning
and only when immutable Contract/Summary/manifest evidence remains.

- [ ] **Step 5: Verify docs and complexity**

```bash
make check-docs-metadata
make check-governance-complexity
```

Expected: documentation checks pass; archive growth is warning-only; Markdown is at most 9550 while the current design and execution plan remain present.

### Task 4: Finish the governed corrective Work Item

**Files:**
- Update: `.ai/work-items/active/release_postmerge_source_verification_v1.summary.json`
- Generate: `.ai/cockpit/current_status.md`
- Archive through `make ai-finish`: `.ai/work-items/archive/**`

**Interfaces:**
- Consumes: verified implementation, tests, docs, and user-authorized zero-net-growth decision.
- Produces: one archived Work Item bundle owned by the corrective PR.

- [ ] **Step 1: Record Summary evidence**

Populate `changedFiles`, `sourcesUsed`, scenario evidence, guideline compliance, both checkpoints, verification results, zero residual release-integrity risks, and the exact archived evidence that justified each historical-plan compaction.

- [ ] **Step 2: Verify the repaid documentation budget**

```bash
make check-governance-complexity
```

Expected: `markdownLines <= 9550`; `archiveGrowth` may warn but must not block.

- [ ] **Step 3: Run the required finish checks**

```bash
make ai-checkpoint \
  CONTRACT=.ai/work-items/active/release_postmerge_source_verification_v1.contract.json \
  SUMMARY=.ai/work-items/active/release_postmerge_source_verification_v1.summary.json \
  STAGE=before_finish
make ai-finish TASK=release_postmerge_source_verification_v1
git add -A
git commit -m "chore: archive release source verification work item"
make check-ai-pr AI_BASE_COMMIT=6c0b8a520c92cfd5cbc699962993d69c433acc6a
```

Expected: all Finish Criteria and PR ownership checks pass with exactly one archived Work Item.

### Task 5: Merge, close, and resume v0.5.39 through a new release Work Item

**Files:** No further files on the corrective branch.

**Interfaces:**
- Consumes: merged corrective PR and synchronized `origin/main`.
- Produces: closed corrective lifecycle, then a separate release-preparation Work Item and exact-SHA publication evidence.

- [ ] **Step 1: Push, open, verify, and merge the corrective PR**

Push `codex/release-postmerge-source-verification`, create one PR, wait for all required checks, and merge only when smoke and compatibility are successful.

- [ ] **Step 2: Close the corrective lifecycle**

```bash
make ai-close-work-item TASK=release_postmerge_source_verification_v1
```

Expected: branch cleanup, clean worktree, and local default branch equality with the remote default branch.

- [ ] **Step 3: Create the serial release-preparation Work Item**

From the new `origin/main`, create a new dedicated branch and
`release_v0539_final_after_source_verification` Contract scoped to release
metadata, freeze, digest, status, and archive evidence. Run its Preflight before
changing metadata.

- [ ] **Step 4: Execute the corrected release preparation lifecycle**

Run candidate verification, `ai-finish`, premerge finalization using candidate
HEAD for content and controlled `origin/main` for identity, `check-release-preflight`,
`check-ai-pr`, PR, merge, and `ai-close-work-item`.

- [ ] **Step 5: Audit and publish exact merged main**

After default-branch synchronization, require successful smoke and
compatibility for the exact main SHA and run:

```bash
make check-release-preflight RELEASE_PREFLIGHT_SOURCE_COMMIT=origin/main
```

Dispatch `.github/workflows/release.yml` for `v0.5.39` with that exact SHA.
Verify the tag target, non-draft Release, archive checksum, SBOM, provenance,
release digests, CI evidence, and `release-source.json` before reporting the
release complete.
