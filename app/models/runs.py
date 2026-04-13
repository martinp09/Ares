from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.commands import CommandPolicy


class RunStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    command_id: str
    business_id: str
    environment: str
    command_type: str
    command_policy: CommandPolicy
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    trigger_run_id: str | None = None
    parent_run_id: str | None = None
    replay_reason: str | None = None
    artifacts: list[dict[str, Any]]
    events: list[dict[str, Any]]


class RunDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    command_id: str
    business_id: str
    environment: str
    command_type: str
    command_policy: CommandPolicy
    status: RunStatus
    trigger_run_id: str | None = None
    parent_run_id: str | None = None
    replay_reason: str | None = None
    artifacts: list[dict[str, Any]]
    events: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class ReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class ReplayResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_run_id: str
    child_run_id: str | None = None
    requires_approval: bool
    approval_id: str | None = None
