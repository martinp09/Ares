from datetime import timedelta

import pytest

from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore, utc_now
from app.db.rbac import RBACRepository
from app.models.permissions import ToolPermissionMode
from app.models.rbac import OrgRoleRecord


def build_repository() -> RBACRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return RBACRepository(client)


def seed_role(
    repository: RBACRepository,
    *,
    role_id: str,
    org_id: str,
    name: str,
    description: str | None = None,
    store_key_name: str | None = None,
    created_at=None,
) -> OrgRoleRecord:
    now = created_at or utc_now()
    role = OrgRoleRecord(
        id=role_id,
        org_id=org_id,
        name=name,
        description=description,
        created_at=now,
        updated_at=now,
    )
    with repository.client.transaction() as store:
        store.roles[role.id] = role
        if store_key_name is not None:
            store.role_keys[(org_id, store_key_name)] = role.id
    return role


def test_role_grants_assignments_and_org_policies_are_deduped() -> None:
    repository = build_repository()

    role = repository.create_role(org_id="org_limitless", name="operator", description="can approve")
    duplicate_role = repository.create_role(org_id="org_limitless", name="operator", description="should update")
    grant = repository.grant_role_permission(role.id, tool_name="publish_campaign", mode=ToolPermissionMode.ALWAYS_ASK)
    duplicate_grant = repository.grant_role_permission(role.id, tool_name="publish_campaign", mode=ToolPermissionMode.FORBIDDEN)
    assignment = repository.assign_role(agent_revision_id="rev_123", role_id=role.id)
    duplicate_assignment = repository.assign_role(agent_revision_id="rev_123", role_id=role.id)
    policy = repository.upsert_org_policy(
        org_id="org_limitless",
        tool_name="publish_campaign",
        mode=ToolPermissionMode.ALWAYS_ASK,
    )
    duplicate_policy = repository.upsert_org_policy(
        org_id="org_limitless",
        tool_name="publish_campaign",
        mode=ToolPermissionMode.FORBIDDEN,
    )

    assert role.id == duplicate_role.id
    assert duplicate_role.description == "should update"
    assert grant.id == duplicate_grant.id
    assert duplicate_grant.mode == ToolPermissionMode.FORBIDDEN
    assert assignment.id == duplicate_assignment.id
    assert policy.id == duplicate_policy.id
    assert duplicate_policy.mode == ToolPermissionMode.FORBIDDEN

    assert [row.name for row in repository.list_roles(org_id="org_limitless")] == ["operator"]
    assert [row.tool_name for row in repository.list_grants(role.id)] == ["publish_campaign"]
    assert [row.role_id for row in repository.list_assignments(agent_revision_id="rev_123")] == [role.id]
    assert [row.tool_name for row in repository.list_org_policies(org_id="org_limitless")] == ["publish_campaign"]


def test_role_names_are_normalized_and_restricted_to_canonical_values() -> None:
    repository = build_repository()

    role = repository.create_role(org_id="org_limitless", name=" Org_Admin ", description="can manage org")

    assert role.name == "org_admin"
    assert repository.get_role_by_name(org_id="org_limitless", name="ORG_ADMIN") == role

    with pytest.raises(ValueError, match="Unsupported role name"):
        repository.create_role(org_id="org_limitless", name="supervisor")

    with pytest.raises(ValueError, match="Unsupported role name"):
        repository.get_role_by_name(org_id="org_limitless", name="supervisor")


def test_effective_permission_resolution_is_deterministic_across_role_insertion_order() -> None:
    repository = build_repository()

    operator_role = repository.create_role(org_id="org_limitless", name="operator")
    org_admin_role = repository.create_role(org_id="org_limitless", name="org_admin")
    repository.grant_role_permission(operator_role.id, tool_name="publish_campaign", mode=ToolPermissionMode.ALWAYS_ALLOW)
    repository.grant_role_permission(org_admin_role.id, tool_name="publish_campaign", mode=ToolPermissionMode.FORBIDDEN)
    repository.assign_role(agent_revision_id="rev_123", role_id=operator_role.id)
    repository.assign_role(agent_revision_id="rev_123", role_id=org_admin_role.id)
    repository.upsert_org_policy(
        org_id="org_limitless",
        tool_name="publish_campaign",
        mode=ToolPermissionMode.ALWAYS_ASK,
    )

    effective = repository.resolve_tool_mode(
        org_id="org_limitless",
        agent_revision_id="rev_123",
        tool_name="publish_campaign",
        default_mode=ToolPermissionMode.ALWAYS_ALLOW,
    )

    assert effective.mode == ToolPermissionMode.FORBIDDEN
    assert effective.source_modes == [
        ToolPermissionMode.FORBIDDEN,
        ToolPermissionMode.ALWAYS_ALLOW,
        ToolPermissionMode.ALWAYS_ASK,
    ]
    assert [(source.source, source.mode) for source in effective.sources] == [
        ("role:org_admin", ToolPermissionMode.FORBIDDEN),
        ("role:operator", ToolPermissionMode.ALWAYS_ALLOW),
        ("org:org_limitless", ToolPermissionMode.ALWAYS_ASK),
    ]


def test_legacy_stored_role_names_do_not_break_reads_or_effective_resolution() -> None:
    repository = build_repository()

    legacy_role = seed_role(
        repository,
        role_id="role_legacy_supervisor",
        org_id="org_limitless",
        name="supervisor",
        store_key_name="supervisor",
    )
    operator_role = repository.create_role(org_id="org_limitless", name="operator")
    repository.grant_role_permission(legacy_role.id, tool_name="publish_campaign", mode=ToolPermissionMode.FORBIDDEN)
    repository.grant_role_permission(operator_role.id, tool_name="publish_campaign", mode=ToolPermissionMode.ALWAYS_ALLOW)
    repository.assign_role(agent_revision_id="rev_legacy", role_id=legacy_role.id)
    repository.assign_role(agent_revision_id="rev_legacy", role_id=operator_role.id)

    assert [role.name for role in repository.list_roles(org_id="org_limitless")] == ["operator", "supervisor"]
    assert [assignment.role_id for assignment in repository.list_assignments("rev_legacy")] == [operator_role.id, legacy_role.id]

    effective = repository.resolve_tool_mode(
        org_id="org_limitless",
        agent_revision_id="rev_legacy",
        tool_name="publish_campaign",
        default_mode=ToolPermissionMode.ALWAYS_ALLOW,
    )

    assert effective.mode == ToolPermissionMode.FORBIDDEN
    assert [(source.source, source.mode) for source in effective.sources] == [
        ("role:operator", ToolPermissionMode.ALWAYS_ALLOW),
        ("role:supervisor", ToolPermissionMode.FORBIDDEN),
    ]


def test_legacy_duplicate_canonicalish_roles_are_collapsed_for_lookup_list_and_create() -> None:
    repository = build_repository()
    first_created_at = utc_now()
    second_created_at = first_created_at + timedelta(seconds=1)

    legacy_role = seed_role(
        repository,
        role_id="role_legacy_org_admin_a",
        org_id="org_limitless",
        name=" Org_Admin ",
        description="legacy description",
        created_at=first_created_at,
    )
    canonical_duplicate = seed_role(
        repository,
        role_id="role_legacy_org_admin_b",
        org_id="org_limitless",
        name="org_admin",
        description="duplicate description",
        store_key_name="org_admin",
        created_at=second_created_at,
    )

    looked_up = repository.get_role_by_name(org_id="org_limitless", name="org_admin")

    assert looked_up is not None
    assert looked_up.id == legacy_role.id

    listed = repository.list_roles(org_id="org_limitless")

    assert [role.id for role in listed] == [legacy_role.id]
    assert [role.name for role in listed] == ["org_admin"]

    updated = repository.create_role(org_id="org_limitless", name="org_admin", description="updated description")

    assert updated.id == legacy_role.id
    assert updated.name == "org_admin"
    assert updated.description == "updated description"
    assert canonical_duplicate.id != updated.id
    assert [role.id for role in repository.list_roles(org_id="org_limitless")] == [legacy_role.id]



def test_legacy_duplicate_canonicalish_roles_are_collapsed_for_effective_resolution() -> None:
    repository = build_repository()
    first_created_at = utc_now()
    second_created_at = first_created_at + timedelta(seconds=1)

    legacy_role = seed_role(
        repository,
        role_id="role_legacy_org_admin_runtime_a",
        org_id="org_limitless",
        name=" Org_Admin ",
        created_at=first_created_at,
    )
    canonical_duplicate = seed_role(
        repository,
        role_id="role_legacy_org_admin_runtime_b",
        org_id="org_limitless",
        name="org_admin",
        store_key_name="org_admin",
        created_at=second_created_at,
    )

    repository.grant_role_permission(
        legacy_role.id,
        tool_name="publish_campaign",
        mode=ToolPermissionMode.ALWAYS_ALLOW,
    )
    repository.grant_role_permission(
        canonical_duplicate.id,
        tool_name="publish_campaign",
        mode=ToolPermissionMode.FORBIDDEN,
    )
    repository.assign_role(agent_revision_id="rev_runtime_legacy", role_id=legacy_role.id)
    repository.assign_role(agent_revision_id="rev_runtime_legacy", role_id=canonical_duplicate.id)

    effective = repository.resolve_tool_mode(
        org_id="org_limitless",
        agent_revision_id="rev_runtime_legacy",
        tool_name="publish_campaign",
        default_mode=ToolPermissionMode.ALWAYS_ALLOW,
    )

    assert effective.mode == ToolPermissionMode.FORBIDDEN
    assert effective.source_modes == [ToolPermissionMode.FORBIDDEN]
    assert [(source.source, source.mode) for source in effective.sources] == [
        ("role:org_admin", ToolPermissionMode.FORBIDDEN),
    ]
