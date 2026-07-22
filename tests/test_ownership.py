import pytest

from ai_ownership import OwnershipError, ownership_decision, ownership_facts, parse_managed_regions


def test_all_ownership_classes_are_explicit_and_project_path_is_not_authority():
    for ownership in ("template", "project", "shared", "generated", "historical"):
        content = (
            "# BEGIN AI COCKPIT MANAGED REGION: ci\nvalue\n# END AI COCKPIT MANAGED REGION: ci\n"
            if ownership == "shared"
            else None
        )
        decision = ownership_decision(
            declared=ownership, path=".ai/project/policy.yaml", content=content
        )
        assert decision["ownership"] == ownership
    assert ownership_decision(declared=None, path=".ai/guards/policy.yaml")["canMutate"] is False


def test_shared_regions_require_explicit_matching_boundaries():
    regions = parse_managed_regions(
        "# BEGIN AI COCKPIT MANAGED REGION: ci\nvalue\n# END AI COCKPIT MANAGED REGION: ci\n"
    )
    assert regions[0].name == "ci"
    assert (
        ownership_decision(declared="shared", path="Makefile", content="# plain\n")["canMutate"]
        is False
    )


@pytest.mark.parametrize(
    "content",
    [
        "# BEGIN AI COCKPIT MANAGED REGION: ci\n",
        "# BEGIN AI COCKPIT MANAGED REGION: ci\n# BEGIN AI COCKPIT MANAGED REGION: nested\n# END AI COCKPIT MANAGED REGION: nested\n# END AI COCKPIT MANAGED REGION: ci\n",
        "# BEGIN AI COCKPIT MANAGED REGION: ci\n# END AI COCKPIT MANAGED REGION: other\n",
        "# BEGIN AI COCKPIT MANAGED REGION: ci\n# END AI COCKPIT MANAGED REGION: ci\n# BEGIN AI COCKPIT MANAGED REGION: ci\n# END AI COCKPIT MANAGED REGION: ci\n",
    ],
)
def test_invalid_region_evidence_fails_closed(content):
    with pytest.raises(OwnershipError):
        parse_managed_regions(content)


def test_historical_and_project_content_are_never_mutable():
    for ownership in ("project", "historical"):
        decision = ownership_decision(declared=ownership, path=".ai/work-items/archive/old.json")
        assert decision["canMutate"] is False


def test_ownership_facts_bind_class_and_modification_to_digests():
    facts = ownership_facts(
        path="src/project.py", ownership="project", installed_digest="a", current_digest="b"
    )
    assert facts == {
        "path": "src/project.py",
        "ownership": "project",
        "ownershipClass": "project_owned",
        "installedDigest": "a",
        "currentDigest": "b",
        "projectModified": True,
    }
