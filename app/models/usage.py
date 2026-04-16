from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ORG_ID


class UsageEventKind(StrEnum):
    RUN = "run"
    SESSION = "session"
    TOOL_CALL = "tool_call"
    PROVIDER_CALL = "provider_call"
    HOST_DISPATCH = "host_dispatch"


class UsageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: UsageEventKind
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    agent_id: str | None = None
    agent_revision_id: str | None = None
    source_kind: str | None = None
    count: int = Field(default=1, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: UsageEventKind
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    agent_id: str | None = None
    agent_revision_id: str | None = None
    source_kind: str | None = None
    count: int = Field(default=1, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class UsageBucketRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    count: int = Field(ge=0)
    last_used_at: datetime | None = None


class UsageSummaryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(ge=0)
    by_kind: dict[str, int] = Field(default_factory=dict)
    by_source_kind: list[UsageBucketRecord] = Field(default_factory=list)
    by_agent: list[UsageBucketRecord] = Field(default_factory=list)
    updated_at: datetime


class UsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    agent_id: str | None = None
    summary: UsageSummaryRecord
    events: list[UsageRecord] = Field(default_factory=list)
