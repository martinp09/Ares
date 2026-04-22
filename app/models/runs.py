from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.agents import AgentRevisionState
from app.models.actors import ActorType
from app.models.commands import CommandPolicy
from app.models.release_management import ReleaseEventType


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
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_classification: str | None = None
    error_message: str | None = None
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
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_classification: str | None = None
    error_message: str | None = None
    artifacts: list[dict[str, Any]]
    events: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class ReplayActorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str
    actor_id: str
    actor_type: ActorType


class ReplayRevisionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str | None = None
    agent_revision_id: str | None = None
    active_revision_id: str | None = None
    revision_state: AgentRevisionState | None = None
    release_channel: str | None = None
    release_event_id: str | None = None
    release_event_type: ReleaseEventType | None = None


class ReplayLineageContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    triggering_actor: ReplayActorRecord
    source: ReplayRevisionContext | None = None
    replay: ReplayRevisionContext | None = None


class ReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class ReplayResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_run_id: str
    child_run_id: str | None = None
    requires_approval: bool
    approval_id: str | None = None
    replay_reason: str | None = None
    lineage: ReplayLineageContext | None = None
