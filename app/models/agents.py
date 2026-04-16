from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.host_adapters import HostAdapterKind
from app.models.providers import ProviderCapability, ProviderKind


class AgentRevisionState(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AgentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(default="default", min_length=1)
    environment: str = Field(default="dev", min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    host_adapter_kind: HostAdapterKind = HostAdapterKind.TRIGGER_DEV
    host_adapter_config: dict[str, Any] = Field(default_factory=dict)
    provider_kind: ProviderKind = ProviderKind.ANTHROPIC
    provider_config: dict[str, Any] = Field(default_factory=dict)
    provider_capabilities: list[ProviderCapability] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)


class AgentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    name: str
    description: str | None = None
    active_revision_id: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentRevisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    revision_number: int
    state: AgentRevisionState
    config: dict[str, Any] = Field(default_factory=dict)
    host_adapter_kind: HostAdapterKind = HostAdapterKind.TRIGGER_DEV
    host_adapter_config: dict[str, Any] = Field(default_factory=dict)
    provider_kind: ProviderKind = ProviderKind.ANTHROPIC
    provider_config: dict[str, Any] = Field(default_factory=dict)
    provider_capabilities: list[ProviderCapability] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    archived_at: datetime | None = None
    cloned_from_revision_id: str | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: AgentRecord
    revisions: list[AgentRevisionRecord]
