from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.commands import CommandCreateRequest, CommandIngestResponse, CommandPolicy
from app.models.permissions import ToolPermissionMode
from app.policies.classifier import apply_policy_precedence
from app.services.command_service import POLICY_BY_COMMAND, command_service
from app.services.permission_service import permission_service


class HermesToolDefinition(BaseModel):
    name: str
    approval_mode: str
    permission_mode: ToolPermissionMode
    payload_schema: dict = Field(default_factory=dict)
    idempotency_scope: str


class HermesToolListResponse(BaseModel):
    tools: list[HermesToolDefinition]


class HermesToolInvokeRequest(BaseModel):
    business_id: int
    environment: str
    idempotency_key: str
    payload: dict = Field(default_factory=dict)
    agent_revision_id: str | None = None


class ToolPermissionError(ValueError):
    pass


PERMISSION_TO_POLICY: dict[ToolPermissionMode, CommandPolicy] = {
    ToolPermissionMode.ALWAYS_ALLOW: CommandPolicy.SAFE_AUTONOMOUS,
    ToolPermissionMode.ALWAYS_ASK: CommandPolicy.APPROVAL_REQUIRED,
    ToolPermissionMode.FORBIDDEN: CommandPolicy.FORBIDDEN,
}


class HermesToolsService:
    def list_tools(self, *, agent_revision_id: str | None = None) -> HermesToolListResponse:
        tools = [
            HermesToolDefinition(
                name=command_type,
                approval_mode=self._resolve_policy(command_type, agent_revision_id).value,
                permission_mode=permission_service.resolve_tool_permission(command_type, agent_revision_id),
                payload_schema={"type": "object"},
                idempotency_scope="business_id + environment + command_type + idempotency_key",
            )
            for command_type in POLICY_BY_COMMAND
        ]
        tools.sort(key=lambda tool: tool.name)
        return HermesToolListResponse(tools=tools)

    def invoke_tool(
        self, tool_name: str, request: HermesToolInvokeRequest
    ) -> tuple[CommandIngestResponse, int]:
        effective_policy = self._resolve_policy(tool_name, request.agent_revision_id)
        if effective_policy == CommandPolicy.FORBIDDEN:
            raise ToolPermissionError(f"Tool '{tool_name}' is forbidden for this agent context")

        command_request = CommandCreateRequest(
            business_id=request.business_id,
            environment=request.environment,
            command_type=tool_name,
            idempotency_key=request.idempotency_key,
            payload=request.payload,
        )
        return command_service.create_command(command_request, policy_override=effective_policy)

    def _resolve_policy(self, tool_name: str, agent_revision_id: str | None) -> CommandPolicy:
        base_policy = command_service.classify(tool_name)
        permission_mode = permission_service.resolve_tool_permission(tool_name, agent_revision_id)
        return apply_policy_precedence(base_policy, PERMISSION_TO_POLICY[permission_mode])


hermes_tools_service = HermesToolsService()
