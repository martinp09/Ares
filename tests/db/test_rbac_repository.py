from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.rbac import RBACRepository
from app.models.permissions import ToolPermissionMode


def build_repository() -> RBACRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return RBACRepository(client)


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
