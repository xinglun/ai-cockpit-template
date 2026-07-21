import hashlib
import json

from scripts import check_release_state_consistency


def write_metadata(tmp_path, *, state=None, published=None, candidate=None):
    published = published or {
        "releaseTag": "v0.5.33",
        "releaseEvidenceAuthority": "release-assets-v1",
        "publicContract": {},
        "capabilities": {},
        "supplyChain": {},
    }
    candidate = candidate or {
        "releaseTag": "v0.5.34",
        "releaseState": "candidate",
        "published": False,
        "basedOnReleaseTag": "v0.5.33",
        "releaseEvidenceAuthority": "release-assets-v1",
        "publicContract": {},
        "capabilities": {},
        "supplyChain": {},
    }
    (tmp_path / "release.json").write_text(json.dumps(published), encoding="utf-8")
    (tmp_path / "next-release.json").write_text(json.dumps(candidate), encoding="utf-8")
    state = state or {
        "state": "candidate_prepared",
        "releaseTag": "v0.5.34",
        "sourceCommit": "c2022fa1d0c2d94ed3edf6c1d16a89260d3fd68f",
        "previousRelease": "v0.5.33",
        "evidenceStatus": "pending_provider_assets",
        "evidenceBundleDigest": None,
    }
    state["metadataDigests"] = {
        "published": hashlib.sha256((tmp_path / "release.json").read_bytes()).hexdigest(),
        "candidate": hashlib.sha256((tmp_path / "next-release.json").read_bytes()).hexdigest(),
    }
    (tmp_path / "release-state.json").write_text(json.dumps(state), encoding="utf-8")


def test_consistent_canonical_state_passes(tmp_path):
    write_metadata(tmp_path)

    assert check_release_state_consistency.check_repository(tmp_path) == []


def test_previous_release_and_candidate_conflicts_are_rejected(tmp_path):
    write_metadata(
        tmp_path,
        state={
            "state": "candidate_prepared",
            "releaseTag": "v0.5.35",
            "sourceCommit": "not-a-sha",
            "previousRelease": "v0.5.34",
            "evidenceStatus": "pending_provider_assets",
            "evidenceBundleDigest": None,
        },
    )

    issues = check_release_state_consistency.check_repository(tmp_path)

    assert any("previousRelease" in issue for issue in issues)
    assert any("candidate releaseTag" in issue for issue in issues)
    assert any("sourceCommit" in issue for issue in issues)


def test_duplicate_candidate_and_digest_drift_are_rejected(tmp_path):
    candidate = {
        "releaseTag": "v0.5.33",
        "releaseState": "candidate",
        "published": False,
        "basedOnReleaseTag": "v0.5.33",
        "releaseEvidenceAuthority": "release-assets-v1",
        "publicContract": {},
        "capabilities": {},
        "supplyChain": {},
    }
    write_metadata(tmp_path, candidate=candidate)
    state = json.loads((tmp_path / "release-state.json").read_text(encoding="utf-8"))
    state["metadataDigests"]["candidate"] = "0" * 64
    (tmp_path / "release-state.json").write_text(json.dumps(state), encoding="utf-8")

    issues = check_release_state_consistency.check_repository(tmp_path)

    assert any("published and candidate tags must be distinct" in issue for issue in issues)
    assert any("metadata digest" in issue for issue in issues)


def test_verified_state_rejects_placeholder_and_accepts_real_digest(tmp_path):
    write_metadata(
        tmp_path,
        state={
            "state": "candidate_verified",
            "releaseTag": "v0.5.34",
            "sourceCommit": "c2022fa1d0c2d94ed3edf6c1d16a89260d3fd68f",
            "previousRelease": "v0.5.33",
            "evidenceStatus": "verified",
            "evidenceBundleDigest": "pending-provider-assets",
        },
    )
    issues = check_release_state_consistency.check_repository(tmp_path)
    assert any("candidate_verified" in issue for issue in issues)

    state = json.loads((tmp_path / "release-state.json").read_text(encoding="utf-8"))
    state["evidenceBundleDigest"] = "a" * 64
    (tmp_path / "release-state.json").write_text(json.dumps(state), encoding="utf-8")
    assert check_release_state_consistency.check_repository(tmp_path) == []
