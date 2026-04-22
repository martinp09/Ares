import pytest

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.organizations import OrganizationsRepository


def build_repository() -> OrganizationsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return OrganizationsRepository(client)


def test_internal_org_is_seeded_and_create_updates_existing_org() -> None:
    repository = build_repository()

    internal = repository.get(DEFAULT_INTERNAL_ORG_ID)
    assert internal is not None
    assert internal.id == DEFAULT_INTERNAL_ORG_ID
    assert internal.is_internal is True

    created = repository.create(id="org_partner", name="Partner Org", slug="partner-org", metadata={"tier": "pilot"})
    updated = repository.create(id="org_partner", name="Partner Org Updated", metadata={"tier": "ga"})

    assert created.id == updated.id
    assert updated.name == "Partner Org Updated"
    assert updated.slug == "partner-org"
    assert updated.metadata == {"tier": "ga"}

    organizations = repository.list()
    assert [organization.id for organization in organizations] == [DEFAULT_INTERNAL_ORG_ID, "org_partner"]


def test_create_with_explicit_org_id_does_not_overwrite_another_org_by_slug() -> None:
    repository = build_repository()

    repository.create(id="org_beta", name="Beta Org", slug="beta-org")

    with pytest.raises(ValueError, match="Organization slug already exists"):
        repository.create(id="org_alpha", name="Alpha Org", slug="beta-org")

    beta = repository.get("org_beta")
    alpha = repository.get("org_alpha")

    assert beta is not None
    assert beta.name == "Beta Org"
    assert alpha is None


def test_updating_slug_releases_the_old_slug_for_reuse() -> None:
    repository = build_repository()

    repository.create(id="org_alpha", name="Alpha Org", slug="alpha-org")
    updated = repository.create(id="org_alpha", name="Alpha Org", slug="beta-org")
    created = repository.create(id="org_gamma", name="Gamma Org", slug="alpha-org")

    assert updated.slug == "beta-org"
    assert created.id == "org_gamma"
    assert created.slug == "alpha-org"
