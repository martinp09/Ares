from __future__ import annotations

from datetime import datetime
from enum import StrEnum
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.models.host_adapters import HostAdapterKind
from app.models.providers import ProviderCapability, ProviderKind


class AgentRevisionState(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AgentVisibility(StrEnum):
    INTERNAL = "internal"
    PRIVATE_CATALOG = "private_catalog"
    MARKETPLACE_CANDIDATE = "marketplace_candidate"
    MARKETPLACE_PUBLISHED = "marketplace_published"


class AgentLifecycleStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


def default_agent_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().casefold()).strip("-")
    return slug or "agent"


class AgentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    business_id: str = Field(default="default", min_length=1)
    environment: str = Field(default="dev", min_length=1)
    name: str = Field(min_length=1)
    slug: str | None = Field(default=None, min_length=1)
    description: str | None = None
    visibility: AgentVisibility = AgentVisibility.INTERNAL
    lifecycle_status: AgentLifecycleStatus = AgentLifecycleStatus.DRAFT
    packaging_metadata: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    host_adapter_kind: HostAdapterKind = HostAdapterKind.TRIGGER_DEV
    host_adapter_config: dict[str, Any] = Field(default_factory=dict)
    provider_kind: ProviderKind = ProviderKind.ANTHROPIC
    provider_config: dict[str, Any] = Field(default_factory=dict)
    provider_capabilities: list[ProviderCapability] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    release_notes: str | None = None
    compatibility_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_initial_lifecycle_status(self) -> "AgentCreateRequest":
        if self.lifecycle_status != AgentLifecycleStatus.DRAFT:
            raise ValueError("New agents must start with lifecycle_status='draft'")
        return self


class AgentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    name: str
    slug: str = Field(min_length=1)
    description: str | None = None
    visibility: AgentVisibility = AgentVisibility.INTERNAL
    lifecycle_status: AgentLifecycleStatus = AgentLifecycleStatus.DRAFT
    packaging_metadata: dict[str, Any] = Field(default_factory=dict)
    active_revision_id: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_slug(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("slug") and data.get("name"):
            return {**data, "slug": default_agent_slug(str(data["name"]))}
        return data


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
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    release_notes: str | None = None
    compatibility_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    archived_at: datetime | None = None
    cloned_from_revision_id: str | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: AgentRecord
    revisions: list[AgentRevisionRecord]
