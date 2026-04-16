from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ORG_ID


class AuditAppendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    resource_type: str | None = None
    resource_id: str | None = None
    agent_id: str | None = None
    agent_revision_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    actor_id: str | None = None
    actor_type: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    resource_type: str | None = None
    resource_id: str | None = None
    agent_id: str | None = None
    agent_revision_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    actor_id: str | None = None
    actor_type: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class AuditListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[AuditRecord] = Field(default_factory=list)
