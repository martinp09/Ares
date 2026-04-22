from __future__ import annotations

from app.db.agents import AgentsRepository
from app.db.permissions import PermissionsRepository
from app.db.rbac import RBACRepository
from app.models.permissions import PermissionListResponse, PermissionRecord, PermissionUpsertRequest, ToolPermissionMode
from app.models.providers import ProviderCapability
from app.services.audit_service import audit_service


class PermissionService:
    def __init__(
        self,
        permissions_repository: PermissionsRepository | None = None,
        rbac_repository: RBACRepository | None = None,
        agents_repository: AgentsRepository | None = None,
    ) -> None:
        self.permissions_repository = permissions_repository or PermissionsRepository()
        self.rbac_repository = rbac_repository or RBACRepository()
        self.agents_repository = agents_repository or AgentsRepository()

    def _get_scoped_revision_and_agent(self, agent_revision_id: str, *, org_id: str | None = None):
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None:
            raise ValueError("Agent revision not found")
        agent = self.agents_repository.get_agent(revision.agent_id)
        if agent is None or (org_id is not None and agent.org_id != org_id):
            raise ValueError("Agent revision not found")
        return revision, agent

    def upsert_permission(self, request: PermissionUpsertRequest, *, org_id: str | None = None) -> PermissionRecord:
        revision, agent = self._get_scoped_revision_and_agent(request.agent_revision_id, org_id=org_id)
        record = self.permissions_repository.upsert(
            agent_revision_id=request.agent_revision_id,
            tool_name=request.tool_name,
            mode=request.mode,
        )
        audit_service.append_event(
            event_type="permission_updated",
            summary=f"Updated permission for {request.tool_name}",
            org_id=agent.org_id,
            resource_type="permission",
            resource_id=record.id,
            agent_id=agent.id,
            agent_revision_id=revision.id,
        )
        return record

    def list_permissions(self, agent_revision_id: str, *, org_id: str | None = None) -> PermissionListResponse:
        self._get_scoped_revision_and_agent(agent_revision_id, org_id=org_id)
        return PermissionListResponse(permissions=self.permissions_repository.list_for_revision(agent_revision_id))

    def resolve_tool_permission(
        self,
        tool_name: str,
        agent_revision_id: str | None = None,
        default_mode: ToolPermissionMode = ToolPermissionMode.ALWAYS_ALLOW,
    ) -> ToolPermissionMode:
        if agent_revision_id is None:
            return default_mode
        revision, agent = self._get_scoped_revision_and_agent(agent_revision_id)
        direct_permission = self.permissions_repository.get(agent_revision_id=agent_revision_id, tool_name=tool_name)
        if direct_permission is not None:
            return direct_permission.mode
        effective = self.rbac_repository.resolve_tool_mode(
            org_id=agent.org_id,
            agent_revision_id=agent_revision_id,
            tool_name=tool_name,
            default_mode=default_mode,
        )
        return effective.mode

    def has_revision_capability(self, agent_revision_id: str, capability: ProviderCapability) -> bool:
        revision, _ = self._get_scoped_revision_and_agent(agent_revision_id)
        if not revision.provider_capabilities:
            return True
        return capability in revision.provider_capabilities


permission_service = PermissionService()
