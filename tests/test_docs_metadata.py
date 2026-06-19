import json
import shutil
from pathlib import Path

from check_docs_metadata import check_repository


ROOT = Path(__file__).resolve().parents[1]


def copy_documentation(target: Path) -> None:
    for name in ("README.md", "README.ja.md", "README.zh-CN.md"):
        shutil.copy2(ROOT / name, target / name)
    shutil.copytree(ROOT / "docs", target / "docs")
    shutil.copytree(ROOT / "examples", target / "examples")
    (target / ".ai").mkdir()
    shutil.copy2(ROOT / ".ai" / "README.md", target / ".ai" / "README.md")
    shutil.copy2(ROOT / ".ai" / "glossary.md", target / ".ai" / "glossary.md")
    shutil.copy2(ROOT / "release.json", target / "release.json")
    shutil.copy2(ROOT / "install.sh", target / "install.sh")


def test_repository_documentation_metadata_is_consistent():
    assert check_repository(ROOT) == []


def test_check_rejects_supported_stack_drift(tmp_path):
    copy_documentation(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8").replace(", android", ""), encoding="utf-8")

    assert "README.md: supported-stack list does not match installer STACKS" in check_repository(tmp_path)


def test_check_rejects_stack_tier_drift(tmp_path):
    copy_documentation(tmp_path)
    readme = tmp_path / "README.zh-CN.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("verified=python,go,rust,typescript", "verified=python"),
        encoding="utf-8",
    )

    assert "README.zh-CN.md: stack compatibility tiers do not match executable CI evidence" in check_repository(tmp_path)


def test_check_rejects_missing_front_matter_field(tmp_path):
    copy_documentation(tmp_path)
    readme = tmp_path / "README.ja.md"
    readme.write_text(readme.read_text(encoding="utf-8").replace("author: Ray\n", ""), encoding="utf-8")

    assert any(error.endswith("README.ja.md: front matter missing author") for error in check_repository(tmp_path))


def test_check_rejects_mutable_or_incomplete_install_commands(tmp_path):
    copy_documentation(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + '\nsh -c "$(curl -fsSL https://raw.githubusercontent.com/xinglun/ai-cockpit-template/main/install.sh)" -- --stack rust\n',
        encoding="utf-8",
    )

    errors = check_repository(tmp_path)
    assert any("remote installer must use a fixed tag or commit" in error for error in errors)
    assert any("install command with --stack requires --update-makefile" in error for error in errors)


def test_check_rejects_unpublished_sha256_claim(tmp_path):
    copy_documentation(tmp_path)
    release = tmp_path / "release.json"
    metadata = json.loads(release.read_text(encoding="utf-8"))
    metadata["capabilities"]["sha256ArchiveVerification"] = False
    release.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\nUse AI_COCKPIT_TEMPLATE_SHA256 for verification.\n",
        encoding="utf-8",
    )

    assert any("SHA256 verification is not published" in error for error in check_repository(tmp_path))


def test_check_rejects_concrete_or_missing_readme_release_resolution(tmp_path):
    copy_documentation(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        .replace("main/release.json", "release-metadata-missing")
        .replace("${RELEASE_TAG}/install.sh", "v9.9.9/install.sh"),
        encoding="utf-8",
    )

    errors = check_repository(tmp_path)
    assert "README.md: primary README must not hardcode a concrete release version" in errors
    assert "README.md: primary install command must resolve the tagged installer from release.json" in errors


def test_check_rejects_known_japanese_style_regressions(tmp_path):
    copy_documentation(tmp_path)
    readme = tmp_path / "README.ja.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\nGemini, Claude, Codex により実行時の安全性を確保します。\n",
        encoding="utf-8",
    )

    errors = check_repository(tmp_path)
    assert sum("Japanese style:" in error for error in errors) == 2
