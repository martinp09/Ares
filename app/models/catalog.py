from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.models.host_adapters import HostAdapterKind
from app.models.providers import ProviderCapability, ProviderKind


class CatalogEntryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    agent_revision_id: str = Field(min_length=1)
    slug: str | None = Field(default=None, min_length=1)
    name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    description: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class CatalogEntryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    agent_id: str = Field(min_length=1)
    agent_revision_id: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    description: str | None = None
    host_adapter_kind: HostAdapterKind
    provider_kind: ProviderKind
    provider_capabilities: list[ProviderCapability] = Field(default_factory=list)
    required_skill_ids: list[str] = Field(default_factory=list)
    required_secret_names: list[str] = Field(default_factory=list)
    release_channel: str = Field(default="internal", min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CatalogEntryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[CatalogEntryRecord] = Field(default_factory=list)
