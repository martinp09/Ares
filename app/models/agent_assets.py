from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentAssetType(StrEnum):
    CALENDAR = "calendar"
    FORM = "form"
    PHONE_NUMBER = "phone_number"
    INBOX = "inbox"
    WEBHOOK = "webhook"


class AgentAssetStatus(StrEnum):
    UNBOUND = "unbound"
    BOUND = "bound"


class AgentAssetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    asset_type: AgentAssetType
    label: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentAssetBindRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_reference: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentAssetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    asset_type: AgentAssetType
    label: str
    connect_later: bool
    status: AgentAssetStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
    binding_reference: str | None = None
    created_at: datetime
    updated_at: datetime
    bound_at: datetime | None = None
