from __future__ import annotations

from app.db.agents import AgentsRepository
from app.db.rbac import RBACRepository
from app.models.permissions import ToolPermissionMode
from app.models.rbac import (
    EffectivePermissionRecord,
    EffectivePermissionResponse,
    OrgPolicyListResponse,
    OrgPolicyRecord,
    OrgPolicyUpsertRequest,
    OrgRoleAssignmentCreateRequest,
    OrgRoleAssignmentListResponse,
    OrgRoleAssignmentRecord,
    OrgRoleCreateRequest,
    OrgRoleGrantCreateRequest,
    OrgRoleGrantListResponse,
    OrgRoleGrantRecord,
    OrgRoleListResponse,
    OrgRoleRecord,
)
from app.services.audit_service import audit_service


class RBACService:
    def __init__(self, repository: RBACRepository | None = None, agents_repository: AgentsRepository | None = None) -> None:
        self.repository = repository or RBACRepository()
        self.agents_repository = agents_repository or AgentsRepository()

    def create_role(self, request: OrgRoleCreateRequest) -> OrgRoleRecord:
        existing_role = self.repository.get_role_by_name(org_id=request.org_id, name=request.name)
        role = self.repository.create_role(org_id=request.org_id, name=request.name, description=request.description)
        audit_service.append_event(
            event_type="role_updated" if existing_role is not None else "role_created",
            summary=f"{'Updated' if existing_role is not None else 'Created'} role {role.name}",
            org_id=role.org_id,
            resource_type="role",
            resource_id=role.id,
            metadata={"name": role.name, "description": role.description},
        )
        return role

    def list_roles(self, org_id: str | None = None) -> OrgRoleListResponse:
        return OrgRoleListResponse(roles=self.repository.list_roles(org_id=org_id))

    def grant_role_permission(self, request: OrgRoleGrantCreateRequest) -> OrgRoleGrantRecord:
        existing_grant = next(
            (grant for grant in self.repository.list_grants(request.role_id) if grant.tool_name == request.tool_name),
            None,
        )
        grant = self.repository.grant_role_permission(request.role_id, tool_name=request.tool_name, mode=request.mode)
        role = self.repository.get_role(request.role_id)
        if role is None:
            raise ValueError("Role not found")
        audit_service.append_event(
            event_type="role_grant_updated" if existing_grant is not None else "role_grant_created",
            summary=f"{'Updated' if existing_grant is not None else 'Granted'} {request.tool_name} for role {request.role_id}",
            org_id=role.org_id,
            resource_type="role_grant",
            resource_id=grant.id,
            metadata={"role_id": request.role_id, "tool_name": request.tool_name, "mode": request.mode.value},
        )
        return grant

    def list_grants(self, role_id: str) -> OrgRoleGrantListResponse:
        return OrgRoleGrantListResponse(grants=self.repository.list_grants(role_id))

    def assign_role(self, request: OrgRoleAssignmentCreateRequest) -> OrgRoleAssignmentRecord:
        existing_assignment = next(
            (assignment for assignment in self.repository.list_assignments(request.agent_revision_id) if assignment.role_id == request.role_id),
            None,
        )
        assignment = self.repository.assign_role(agent_revision_id=request.agent_revision_id, role_id=request.role_id)
        role = self.repository.get_role(request.role_id)
        if role is None:
            raise ValueError("Role not found")
        audit_service.append_event(
            event_type="role_assignment_updated" if existing_assignment is not None else "role_assignment_created",
            summary=f"{'Updated' if existing_assignment is not None else 'Assigned'} role {request.role_id}",
            org_id=role.org_id,
            resource_type="role_assignment",
            resource_id=assignment.id,
            agent_revision_id=request.agent_revision_id,
            metadata={"agent_revision_id": request.agent_revision_id, "role_id": request.role_id},
        )
        return assignment

    def list_assignments(self, agent_revision_id: str) -> OrgRoleAssignmentListResponse:
        return OrgRoleAssignmentListResponse(assignments=self.repository.list_assignments(agent_revision_id))

    def upsert_org_policy(self, request: OrgPolicyUpsertRequest) -> OrgPolicyRecord:
        existing_policy = next(
            (policy for policy in self.repository.list_org_policies(org_id=request.org_id) if policy.tool_name == request.tool_name),
            None,
        )
        policy = self.repository.upsert_org_policy(org_id=request.org_id, tool_name=request.tool_name, mode=request.mode)
        audit_service.append_event(
            event_type="org_policy_updated" if existing_policy is not None else "org_policy_created",
            summary=f"{'Updated' if existing_policy is not None else 'Upserted'} org policy for {request.tool_name}",
            org_id=policy.org_id,
            resource_type="org_policy",
            resource_id=policy.id,
            metadata={"tool_name": policy.tool_name, "mode": policy.mode.value},
        )
        return policy

    def list_org_policies(self, org_id: str | None = None) -> OrgPolicyListResponse:
        return OrgPolicyListResponse(policies=self.repository.list_org_policies(org_id=org_id))

    def resolve_effective_permission(
        self,
        *,
        agent_revision_id: str,
        tool_name: str,
        default_mode: ToolPermissionMode = ToolPermissionMode.ALWAYS_ALLOW,
    ) -> EffectivePermissionRecord:
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None:
            raise ValueError("Agent revision not found")
        agent = self.agents_repository.get_agent(revision.agent_id)
        if agent is None:
            raise ValueError("Agent not found")
        return self.repository.resolve_tool_mode(
            org_id=agent.org_id,
            agent_revision_id=agent_revision_id,
            tool_name=tool_name,
            default_mode=default_mode,
        )

    def list_effective_permissions(self, agent_revision_id: str) -> list[EffectivePermissionRecord]:
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None:
            raise ValueError("Agent revision not found")
        agent = self.agents_repository.get_agent(revision.agent_id)
        if agent is None:
            raise ValueError("Agent not found")
        tool_names = self.repository.list_effective_tool_names(org_id=agent.org_id, agent_revision_id=agent_revision_id)
        return [
            self.repository.resolve_tool_mode(
                org_id=agent.org_id,
                agent_revision_id=agent_revision_id,
                tool_name=tool_name,
                default_mode=ToolPermissionMode.ALWAYS_ALLOW,
            )
            for tool_name in tool_names
        ]

    def resolve_effective_response(self, *, agent_revision_id: str, tool_name: str) -> EffectivePermissionResponse:
        effective = self.resolve_effective_permission(agent_revision_id=agent_revision_id, tool_name=tool_name)
        return EffectivePermissionResponse(
            tool_name=effective.tool_name,
            mode=effective.mode,
            source_modes=effective.source_modes,
            sources=effective.sources,
        )


rbac_service = RBACService()
