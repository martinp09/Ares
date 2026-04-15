from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ToolPermissionMode(StrEnum):
    ALWAYS_ALLOW = "always_allow"
    ALWAYS_ASK = "always_ask"
    FORBIDDEN = "forbidden"


class PermissionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_revision_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    mode: ToolPermissionMode
    created_at: datetime
    updated_at: datetime


class PermissionUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_revision_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    mode: ToolPermissionMode


class PermissionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permissions: list[PermissionRecord]
