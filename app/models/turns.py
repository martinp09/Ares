from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TurnStatus(StrEnum):
    RUNNING = "running"
    WAITING_FOR_TOOL = "waiting_for_tool"
    COMPLETED = "completed"
    FAILED = "failed"


class TurnEventType(StrEnum):
    TURN_STARTED = "turn_started"
    TURN_RESUMED = "turn_resumed"
    TURN_WAITING_FOR_TOOL = "turn_waiting_for_tool"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    TOOL_RESULT_RECORDED = "tool_result_recorded"
    TURN_COMPLETED = "turn_completed"
    TURN_FAILED = "turn_failed"


class TurnToolCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class TurnToolResultRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: str = Field(min_length=1)
    output: dict[str, Any] = Field(default_factory=dict)
    success: bool = True


class TurnEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    turn_id: str
    session_id: str
    event_type: TurnEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    sequence_number: int
    created_at: datetime


class TurnRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    agent_id: str
    agent_revision_id: str
    turn_number: int
    status: TurnStatus
    input_message: str | None = None
    assistant_message: str | None = None
    tool_calls: list[TurnToolCallRecord] = Field(default_factory=list)
    tool_results: list[TurnToolResultRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    resumed_from_turn_id: str | None = None
    created_at: datetime
    updated_at: datetime


class TurnStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_message: str | None = None
    assistant_message: str | None = None
    tool_calls: list[TurnToolCallRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TurnResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assistant_message: str | None = None
    tool_results: list[TurnToolResultRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
