from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.permissions import ToolPermissionMode


class ToolHookPhase(StrEnum):
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"


class ToolHookContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: ToolHookPhase
    tool_name: str
    agent_revision_id: str | None = None
    business_id: str
    environment: str
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    approval_mode: str
    permission_mode: ToolPermissionMode
    capability_allowed: bool = True
    success: bool | None = None
    status_code: int | None = None
    command: dict[str, Any] | None = None
    error_message: str | None = None
