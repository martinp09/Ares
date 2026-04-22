from app.core.config import DEFAULT_INTERNAL_ACTOR_ID, DEFAULT_INTERNAL_ORG_ID
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.memberships import MembershipsRepository


def build_repository() -> MembershipsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return MembershipsRepository(client)


def test_internal_membership_is_seeded_and_memberships_are_deduped_by_org_and_actor() -> None:
    repository = build_repository()

    internal = repository.get_by_actor(org_id=DEFAULT_INTERNAL_ORG_ID, actor_id=DEFAULT_INTERNAL_ACTOR_ID)
    assert internal is not None
    assert internal.org_id == DEFAULT_INTERNAL_ORG_ID
    assert internal.actor_id == DEFAULT_INTERNAL_ACTOR_ID

    created = repository.upsert(
        org_id="org_partner",
        actor_id="actor_jane",
        actor_type="user",
        member_id="member_jane",
        name="Jane Doe",
        role_name="viewer",
        metadata={"source": "invite"},
    )
    updated = repository.upsert(
        org_id="org_partner",
        actor_id="actor_jane",
        actor_type="user",
        member_id="member_jane",
        name="Jane Doe",
        role_name="admin",
        metadata={"source": "sso"},
    )

    assert created.id == updated.id
    assert updated.role_name == "admin"
    assert updated.metadata == {"source": "sso"}

    org_memberships = repository.list_for_org("org_partner")
    actor_memberships = repository.list_for_actor("actor_jane")

    assert [membership.id for membership in org_memberships] == [created.id]
    assert [membership.id for membership in actor_memberships] == [created.id]
