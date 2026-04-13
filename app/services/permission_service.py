from __future__ import annotations

from app.db.agents import AgentsRepository
from app.db.permissions import PermissionsRepository
from app.models.permissions import PermissionListResponse, PermissionRecord, PermissionUpsertRequest, ToolPermissionMode


class PermissionService:
    def __init__(
        self,
        permissions_repository: PermissionsRepository | None = None,
        agents_repository: AgentsRepository | None = None,
    ) -> None:
        self.permissions_repository = permissions_repository or PermissionsRepository()
        self.agents_repository = agents_repository or AgentsRepository()

    def upsert_permission(self, request: PermissionUpsertRequest) -> PermissionRecord:
        revision = self.agents_repository.get_revision(request.agent_revision_id)
        if revision is None:
            raise ValueError("Agent revision not found")
        return self.permissions_repository.upsert(
            agent_revision_id=request.agent_revision_id,
            tool_name=request.tool_name,
            mode=request.mode,
        )

    def list_permissions(self, agent_revision_id: str) -> PermissionListResponse:
        return PermissionListResponse(permissions=self.permissions_repository.list_for_revision(agent_revision_id))

    def resolve_tool_permission(
        self,
        tool_name: str,
        agent_revision_id: str | None = None,
        default_mode: ToolPermissionMode = ToolPermissionMode.ALWAYS_ALLOW,
    ) -> ToolPermissionMode:
        if agent_revision_id is None:
            return default_mode
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None:
            raise ValueError("Agent revision not found")
        permission = self.permissions_repository.get(agent_revision_id=agent_revision_id, tool_name=tool_name)
        if permission is None:
            return default_mode
        return permission.mode


permission_service = PermissionService()
