from __future__ import annotations

from pydantic import BaseModel, Field

from app.db.agents import AgentsRepository
from app.models.commands import CommandCreateRequest, CommandIngestResponse, CommandPolicy
from app.models.permissions import ToolPermissionMode
from app.models.providers import ProviderCapability
from app.models.tool_hooks import ToolHookContext
from app.policies.classifier import apply_policy_precedence
from app.services.command_service import POLICY_BY_COMMAND, command_service as default_command_service
from app.services.permission_service import permission_service as default_permission_service
from app.services.skill_registry_service import SkillRegistryService, skill_registry_service as default_skill_registry_service
from app.services.tool_hook_service import ToolHookService, tool_hook_service as default_tool_hook_service


class HermesToolDefinition(BaseModel):
    name: str
    approval_mode: str
    permission_mode: ToolPermissionMode
    capability_allowed: bool = True
    payload_schema: dict = Field(default_factory=dict)
    idempotency_scope: str


class HermesToolListResponse(BaseModel):
    tools: list[HermesToolDefinition]


class HermesToolInvokeRequest(BaseModel):
    business_id: str
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
    def __init__(
        self,
        *,
        permission_service=default_permission_service,
        command_service=default_command_service,
        tool_hook_service: ToolHookService = default_tool_hook_service,
        agents_repository: AgentsRepository | None = None,
        skill_registry_service: SkillRegistryService = default_skill_registry_service,
    ) -> None:
        self.permission_service = permission_service
        self.command_service = command_service
        self.tool_hook_service = tool_hook_service
        self.agents_repository = agents_repository or AgentsRepository()
        self.skill_registry_service = skill_registry_service

    def list_tools(self, *, agent_revision_id: str | None = None) -> HermesToolListResponse:
        capability_allowed = self._tool_calls_allowed(agent_revision_id)
        allowed_command_surface = self._resolve_command_surface(agent_revision_id)
        tools = [
            HermesToolDefinition(
                name=command_type,
                approval_mode=self._resolve_policy(command_type, agent_revision_id).value,
                permission_mode=self._resolve_permission_mode(command_type, agent_revision_id),
                capability_allowed=capability_allowed,
                payload_schema={"type": "object"},
                idempotency_scope="business_id + environment + command_type + idempotency_key",
            )
            for command_type in (allowed_command_surface or POLICY_BY_COMMAND)
        ]
        tools.sort(key=lambda tool: tool.name)
        return HermesToolListResponse(tools=tools)

    def invoke_tool(
        self, tool_name: str, request: HermesToolInvokeRequest
    ) -> tuple[CommandIngestResponse, int]:
        capability_allowed = self._tool_calls_allowed(request.agent_revision_id)
        if not capability_allowed:
            raise ToolPermissionError(f"Tool '{tool_name}' is not allowed for this agent capability set")

        allowed_command_surface = self._resolve_command_surface(request.agent_revision_id)
        if (
            allowed_command_surface is not None
            and tool_name in POLICY_BY_COMMAND
            and tool_name not in allowed_command_surface
        ):
            raise ToolPermissionError(f"Tool '{tool_name}' is not allowed for this agent skill surface")

        permission_mode = self._resolve_permission_mode(tool_name, request.agent_revision_id)
        effective_policy = apply_policy_precedence(
            self.command_service.classify(tool_name),
            PERMISSION_TO_POLICY[permission_mode],
        )
        if effective_policy == CommandPolicy.FORBIDDEN:
            raise ToolPermissionError(f"Tool '{tool_name}' is forbidden for this agent context")

        hook_context = ToolHookContext(
            phase="before_tool_call",
            tool_name=tool_name,
            agent_revision_id=request.agent_revision_id,
            business_id=request.business_id,
            environment=request.environment,
            idempotency_key=request.idempotency_key,
            payload=dict(request.payload),
            approval_mode=effective_policy.value,
            permission_mode=permission_mode,
            capability_allowed=capability_allowed,
        )
        self.tool_hook_service.before_tool_call(hook_context)

        command_request = CommandCreateRequest(
            business_id=request.business_id,
            environment=request.environment,
            command_type=tool_name,
            idempotency_key=request.idempotency_key,
            payload=request.payload,
            agent_revision_id=request.agent_revision_id,
        )
        try:
            command_response, status_code = self.command_service.create_command(command_request, policy_override=effective_policy)
        except Exception as exc:
            self.tool_hook_service.after_tool_call(
                hook_context.model_copy(
                    update={
                        "phase": "after_tool_call",
                        "success": False,
                        "error_message": str(exc),
                    }
                )
            )
            raise

        self.tool_hook_service.after_tool_call(
            hook_context.model_copy(
                update={
                    "phase": "after_tool_call",
                    "success": True,
                    "status_code": status_code,
                    "command": command_response.model_dump(mode="json"),
                }
            )
        )
        return command_response, status_code

    def _resolve_policy(self, tool_name: str, agent_revision_id: str | None) -> CommandPolicy:
        base_policy = self.command_service.classify(tool_name)
        permission_mode = self._resolve_permission_mode(tool_name, agent_revision_id)
        return apply_policy_precedence(base_policy, PERMISSION_TO_POLICY[permission_mode])

    def _resolve_permission_mode(self, tool_name: str, agent_revision_id: str | None) -> ToolPermissionMode:
        return self.permission_service.resolve_tool_permission(tool_name, agent_revision_id)

    def _resolve_command_surface(self, agent_revision_id: str | None) -> set[str] | None:
        if agent_revision_id is None:
            return None
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None or not revision.skill_ids:
            return None

        skills = self.skill_registry_service.resolve_skills(revision.skill_ids)
        allowed_command_surface = {
            required_tool
            for skill in skills
            for required_tool in skill.required_tools
            if required_tool in POLICY_BY_COMMAND
        }
        return allowed_command_surface or None

    def _tool_calls_allowed(self, agent_revision_id: str | None) -> bool:
        if agent_revision_id is None:
            return True
        return self.permission_service.has_revision_capability(agent_revision_id, ProviderCapability.TOOL_CALLS)


hermes_tools_service = HermesToolsService()
