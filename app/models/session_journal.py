from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.turns import TurnStatus


class SessionCompactionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_version: int = Field(default=0, ge=0)
    compacted_turn_count: int = Field(default=0, ge=0)
    compacted_through_turn_id: str | None = None
    compacted_through_turn_number: int = Field(default=0, ge=0)
    source_event_count: int = Field(default=0, ge=0)
    last_compacted_at: datetime | None = None


class SessionToolResultSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool = True
    output: dict[str, Any] = Field(default_factory=dict)


class SessionToolInteractionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: SessionToolResultSummary | None = None


class SessionCompactedTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: str
    turn_number: int = Field(ge=1)
    status: TurnStatus
    input_message: str | None = None
    assistant_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)
    completed_work: list[str] = Field(default_factory=list)
    pending_work: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    tool_interactions: list[SessionToolInteractionSummary] = Field(default_factory=list)


class SessionMemorySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    summary_version: int = Field(ge=1)
    compacted_turn_ids: list[str] = Field(default_factory=list)
    compacted_turn_count: int = Field(ge=0)
    compacted_through_turn_id: str | None = None
    compacted_through_turn_number: int = Field(default=0, ge=0)
    source_event_count: int = Field(default=0, ge=0)
    goals: list[str] = Field(default_factory=list)
    completed_work: list[str] = Field(default_factory=list)
    pending_work: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    turns: list[SessionCompactedTurn] = Field(default_factory=list)
    continuation_prompt: str = ""
    updated_at: datetime


class SessionJournalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    agent_id: str
    agent_revision_id: str
    business_id: str
    environment: str
    status: str
    timeline_length: int = Field(default=0, ge=0)
    turn_count: int = Field(default=0, ge=0)
    compaction: SessionCompactionState = Field(default_factory=SessionCompactionState)
    memory_summary: SessionMemorySummary | None = None
