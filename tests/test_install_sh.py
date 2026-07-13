from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_remote_archive_url_supports_branch_tag_and_sha_refs():
    script = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert 'git clone --depth 1 --branch "$REF" --single-branch "$URL" "$SOURCE"' in script
    assert (
        'git -C "$SOURCE" archive --format=tar.gz --prefix=ai-cockpit/ HEAD -o "$ARCHIVE"' in script
    )
    assert (
        'EXPECTED_SHA256="${AI_COCKPIT_TEMPLATE_SHA256:-01edf23ddf7a6af55d8c3e0d6065ab61f391a799af496cd934e7aa390ce093b4}"'
        in script
    )
