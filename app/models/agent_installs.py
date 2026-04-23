from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.models.agents import AgentRecord, AgentRevisionRecord


class AgentInstallCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_entry_id: str = Field(min_length=1)
    business_id: str = Field(default="default", min_length=1)
    environment: str = Field(default="dev", min_length=1)
    name: str | None = Field(default=None, min_length=1)
    slug: str | None = Field(default=None, min_length=1)
    description: str | None = None


class AgentInstallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    catalog_entry_id: str = Field(min_length=1)
    source_agent_id: str = Field(min_length=1)
    source_agent_revision_id: str = Field(min_length=1)
    installed_agent_id: str = Field(min_length=1)
    installed_agent_revision_id: str = Field(min_length=1)
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime


class AgentInstallResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    install: AgentInstallRecord
    agent: AgentRecord
    revisions: list[AgentRevisionRecord]


class AgentInstallListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    installs: list[AgentInstallRecord] = Field(default_factory=list)
