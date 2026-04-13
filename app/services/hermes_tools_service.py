from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.commands import CommandCreateRequest, CommandIngestResponse
from app.services.command_service import POLICY_BY_COMMAND, command_service


class HermesToolDefinition(BaseModel):
    name: str
    approval_mode: str
    payload_schema: dict = Field(default_factory=dict)
    idempotency_scope: str


class HermesToolListResponse(BaseModel):
    tools: list[HermesToolDefinition]


class HermesToolInvokeRequest(BaseModel):
    business_id: str
    environment: str
    idempotency_key: str
    payload: dict = Field(default_factory=dict)


class HermesToolsService:
    def list_tools(self) -> HermesToolListResponse:
        tools = [
            HermesToolDefinition(
                name=command_type,
                approval_mode=policy.value,
                payload_schema={"type": "object"},
                idempotency_scope="business_id + environment + command_type + idempotency_key",
            )
            for command_type, policy in POLICY_BY_COMMAND.items()
        ]
        tools.sort(key=lambda tool: tool.name)
        return HermesToolListResponse(tools=tools)

    def invoke_tool(
        self, tool_name: str, request: HermesToolInvokeRequest
    ) -> tuple[CommandIngestResponse, int]:
        command_request = CommandCreateRequest(
            business_id=request.business_id,
            environment=request.environment,
            command_type=tool_name,
            idempotency_key=request.idempotency_key,
            payload=request.payload,
        )
        return command_service.create_command(command_request)


hermes_tools_service = HermesToolsService()
