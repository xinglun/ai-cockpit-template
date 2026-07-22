import hashlib
import json
import sys
from pathlib import Path

import pytest

import verify_quick_install_release as verifier


SOURCE_COMMIT = "a" * 40


def make_contract(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "source"
    root.mkdir()
    installer = root / "install.sh"
    installer.write_bytes(b"#!/bin/sh\necho install\n")
    installer.chmod(0o755)
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"release archive bytes")
    metadata = {
        "releaseTag": "v1.2.3",
        "sourceCommit": SOURCE_COMMIT,
        "installerDigest": hashlib.sha256(installer.read_bytes()).hexdigest(),
        "releaseArchive": {
            "assetName": archive.name,
            "sourceCommit": SOURCE_COMMIT,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "url": archive.as_uri(),
        },
        "capabilities": {"sha256ArchiveVerification": {"supported": True, "verified": True}},
    }
    (root / "release.json").write_text(json.dumps(metadata), encoding="utf-8")
    return root, archive


def test_quick_install_release_contract_verifies_all_bindings(monkeypatch, tmp_path):
    root, _archive = make_contract(tmp_path)
    monkeypatch.setattr(verifier, "run_git", lambda *_args: SOURCE_COMMIT)

    evidence = verifier.verify_release(root, ref="v1.2.3")

    assert evidence["sourceCommit"] == SOURCE_COMMIT
    assert evidence["assetName"] == "source.tar.gz"


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (lambda data: data.update(releaseTag="v9.9.9"), "release tag mismatch"),
        (lambda data: data.update(sourceCommit="b" * 40), "source commit mismatch"),
        (lambda data: data.update(installerDigest="0" * 64), "installer digest mismatch"),
        (lambda data: data["releaseArchive"].update(sha256="0" * 64), "archive SHA256 mismatch"),
        (lambda data: data.pop("releaseArchive"), "releaseArchive evidence is missing"),
    ],
)
def test_quick_install_release_contract_fails_closed(monkeypatch, tmp_path, change, expected):
    root, _archive = make_contract(tmp_path)
    metadata_path = root / "release.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    change(metadata)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(verifier, "run_git", lambda *_args: SOURCE_COMMIT)

    with pytest.raises(verifier.ReleaseVerificationError, match=expected):
        verifier.verify_release(root, ref="v1.2.3")


def test_unverified_capability_fails_closed_before_download(monkeypatch, tmp_path):
    root, _archive = make_contract(tmp_path)
    metadata_path = root / "release.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["capabilities"]["sha256ArchiveVerification"]["verified"] = False
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(verifier, "run_git", lambda *_args: SOURCE_COMMIT)

    with pytest.raises(verifier.ReleaseVerificationError, match="not verified"):
        verifier.verify_release(root, ref="v1.2.3")


def test_legacy_capability_shape_is_supported(monkeypatch, tmp_path):
    root, _archive = make_contract(tmp_path)
    metadata_path = root / "release.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["capabilities"]["sha256ArchiveVerification"] = True
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(verifier, "run_git", lambda *_args: SOURCE_COMMIT)

    assert verifier.verify_release(root, ref="v1.2.3")["releaseTag"] == "v1.2.3"


def test_candidate_metadata_presence_is_ignored_and_tag_failure_is_wrapped(monkeypatch, tmp_path):
    root, _archive = make_contract(tmp_path)
    (root / "next-release.json").write_text('{"releaseTag":"v9.9.9"}', encoding="utf-8")
    assert verifier.load_release_metadata(root)["releaseTag"] == "v1.2.3"

    def fake_git(*_args):
        raise verifier.ReleaseVerificationError("tag unavailable")

    monkeypatch.setattr(verifier, "run_git", fake_git)
    with pytest.raises(verifier.ReleaseVerificationError, match="unavailable locally"):
        verifier.verify_release(root, ref="v1.2.3")


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (lambda data: data.update(sourceCommit="bad"), "release.json sourceCommit is invalid"),
        (lambda data: data.update(installerDigest="bad"), "installerDigest is missing or invalid"),
        (
            lambda data: data["releaseArchive"].update(sourceCommit="b" * 40),
            "releaseArchive.sourceCommit",
        ),
        (lambda data: data["releaseArchive"].update(assetName="nested/file.tgz"), "unsafe"),
        (lambda data: data["releaseArchive"].update(sha256="bad"), "sha256 is missing or invalid"),
        (lambda data: data["releaseArchive"].pop("url"), "url is missing"),
        (
            lambda data: data["releaseArchive"].update(url="https://example.invalid/other.tgz"),
            "release archive URL does not name",
        ),
        (
            lambda data: data["releaseArchive"].update(url="file:///tmp/missing.tgz"),
            "release archive asset is unavailable",
        ),
    ],
)
def test_release_contract_rejects_additional_archive_failures(
    monkeypatch, tmp_path, change, expected
):
    root, _archive = make_contract(tmp_path)
    metadata_path = root / "release.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    change(metadata)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(verifier, "run_git", lambda *_args: SOURCE_COMMIT)

    with pytest.raises(verifier.ReleaseVerificationError, match=expected):
        verifier.verify_release(root, ref="v1.2.3")


def test_unsupported_capability_fails_closed(monkeypatch, tmp_path):
    root, _archive = make_contract(tmp_path)
    metadata_path = root / "release.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["capabilities"]["sha256ArchiveVerification"]["supported"] = False
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(verifier, "run_git", lambda *_args: SOURCE_COMMIT)

    with pytest.raises(verifier.ReleaseVerificationError, match="support"):
        verifier.verify_release(root, ref="v1.2.3")


def test_invalid_metadata_and_git_failure_are_reported(monkeypatch, tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "release.json").write_text("[]", encoding="utf-8")
    with pytest.raises(verifier.ReleaseVerificationError, match="object"):
        verifier.load_release_metadata(root)

    (root / "release.json").write_text("{", encoding="utf-8")
    with pytest.raises(verifier.ReleaseVerificationError, match="unreadable"):
        verifier.load_release_metadata(root)

    monkeypatch.setattr(
        verifier.subprocess,
        "run",
        lambda *_args, **_kwargs: type("R", (), {"returncode": 1, "stderr": "no git"})(),
    )
    with pytest.raises(verifier.ReleaseVerificationError, match="failed"):
        verifier.run_git(root, "status")


def test_cli_reports_verification_failure(monkeypatch, tmp_path, capsys):
    root, _archive = make_contract(tmp_path)
    monkeypatch.setattr(
        verifier,
        "verify_release",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            verifier.ReleaseVerificationError("bad evidence")
        ),
    )
    monkeypatch.setattr(sys, "argv", ["verify", "--root", str(root), "--ref", "v1.2.3"])

    assert verifier.main() == 2
    assert "Quick Install release verification failed" in capsys.readouterr().err
