import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_install_help_identifies_canonical_repository():
    script = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "AI_COCKPIT_TEMPLATE_REPO=spirex-ds-dev/ai-cockpit-template" in script


def test_remote_archive_url_supports_branch_tag_and_sha_refs():
    script = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert 'git clone --depth 1 --branch "$REF" --single-branch "$URL" "$SOURCE"' in script
    assert 'python3 "$SOURCE/scripts/verify_quick_install_release.py"' in script
    assert 'EXPECTED_SHA256="${AI_COCKPIT_TEMPLATE_SHA256:-}"' in script
    assert "http://*|https://*|git@*)" in script
    assert 'URL="$REPO"' in script
    assert "verify_quick_install_release.py" in script
    assert "release.json remains authoritative" in script


def test_quick_install_does_not_reference_candidate_release_metadata():
    script = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "next-release.json" not in script
    release_tag = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))["releaseTag"]
    assert f'REF="${{AI_COCKPIT_TEMPLATE_REF:-{release_tag}}}"' in script
