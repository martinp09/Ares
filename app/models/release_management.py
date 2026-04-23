from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.models.actors import ActorType
from app.models.agents import AgentRecord, AgentRevisionRecord
from app.models.outcomes import OutcomeEvaluationPayload, ReleaseDecisionEvaluationSummary


class ReleaseEventType(StrEnum):
    PUBLISH = "publish"
    ROLLBACK = "rollback"
    DEACTIVATE = "deactivate"


class ReleaseTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None
    evaluation_summary: OutcomeEvaluationPayload | None = None
    require_passing_evaluation: bool = False
    rollback_reason: str | None = None


class ReleaseEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    agent_id: str = Field(min_length=1)
    event_type: ReleaseEventType
    actor_id: str = Field(min_length=1)
    actor_type: ActorType
    previous_active_revision_id: str | None = None
    target_revision_id: str = Field(min_length=1)
    resulting_active_revision_id: str | None = None
    release_channel: str | None = None
    notes: str | None = None
    evaluation_summary: ReleaseDecisionEvaluationSummary | None = None
    created_at: datetime
    updated_at: datetime


class ReleaseTransitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: AgentRecord
    revisions: list[AgentRevisionRecord]
    event: ReleaseEventRecord


class ReleaseEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[ReleaseEventRecord]
