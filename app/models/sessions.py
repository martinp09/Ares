from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.session_journal import SessionCompactionState


class SessionStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class SessionTimelineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SessionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    agent_revision_id: str
    business_id: str
    environment: str
    status: SessionStatus
    timeline: list[SessionTimelineEntry] = Field(default_factory=list)
    compaction: SessionCompactionState = Field(default_factory=SessionCompactionState)
    created_at: datetime
    updated_at: datetime


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_revision_id: str
    business_id: str
    environment: str
    initial_message: str | None = None


class SessionAppendEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class SessionCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: SessionRecord
