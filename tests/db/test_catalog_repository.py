from app.db.catalog import CatalogRepository
from app.db.client import reset_control_plane_store
from app.models.host_adapters import HostAdapterKind
from app.models.providers import ProviderCapability, ProviderKind


def test_catalog_repository_creates_and_lists_entries_by_org() -> None:
    reset_control_plane_store()
    repository = CatalogRepository()

    alpha_entry = repository.create(
        org_id="org_alpha",
        agent_id="agt_alpha",
        agent_revision_id="rev_alpha",
        slug="seller-ops",
        name="Seller Ops",
        summary="Internal seller ops package",
        description="Alpha org internal package",
        visibility="private_catalog",
        host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
        provider_kind=ProviderKind.ANTHROPIC,
        provider_capabilities=[ProviderCapability.TOOL_CALLS],
        required_skill_ids=["skl_triage"],
        required_secret_names=["resend_api_key"],
        release_channel="dogfood",
    )
    beta_entry = repository.create(
        org_id="org_beta",
        agent_id="agt_beta",
        agent_revision_id="rev_beta",
        slug="seller-ops",
        name="Seller Ops",
        summary="Beta org package",
        description=None,
        visibility="marketplace_candidate",
        host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
        provider_kind=ProviderKind.ANTHROPIC,
        provider_capabilities=[],
        release_channel="internal",
    )

    assert repository.get(alpha_entry.id) == alpha_entry
    assert alpha_entry.visibility == "private_catalog"
    assert alpha_entry.marketplace_publication_enabled is False
    assert beta_entry.visibility == "marketplace_candidate"
    assert [entry.id for entry in repository.list(org_id="org_alpha")] == [alpha_entry.id]
    assert [entry.id for entry in repository.list(org_id="org_beta")] == [beta_entry.id]


def test_catalog_repository_rejects_duplicate_slugs_within_an_org() -> None:
    reset_control_plane_store()
    repository = CatalogRepository()

    repository.create(
        org_id="org_alpha",
        agent_id="agt_alpha",
        agent_revision_id="rev_alpha",
        slug="seller-ops",
        name="Seller Ops",
        summary="Internal seller ops package",
        description=None,
        visibility="private_catalog",
        host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
        provider_kind=ProviderKind.ANTHROPIC,
        provider_capabilities=[],
    )

    try:
        repository.create(
            org_id="org_alpha",
            agent_id="agt_alpha_2",
            agent_revision_id="rev_alpha_2",
            slug="seller-ops",
            name="Seller Ops Copy",
            summary="Should fail",
            description=None,
            visibility="private_catalog",
            host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
            provider_kind=ProviderKind.ANTHROPIC,
            provider_capabilities=[],
        )
    except ValueError as exc:
        assert "slug already exists" in str(exc).lower()
    else:
        raise AssertionError("Expected duplicate catalog slug to raise ValueError")
