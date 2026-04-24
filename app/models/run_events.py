from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.runs import RunStatus


class RunLifecycleEvent(StrEnum):
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    ARTIFACT_PRODUCED = "artifact_produced"


class RunStartedCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_run_id: str | None = None
    command_id: str | None = None
    business_id: str | None = None
    environment: str | None = None
    idempotency_key: str | None = None
    started_at: datetime | None = None


class RunCompletedCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_run_id: str | None = None
    command_id: str | None = None
    business_id: str | None = None
    environment: str | None = None
    idempotency_key: str | None = None
    completed_at: datetime | None = None


class RunFailedCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_run_id: str | None = None
    command_id: str | None = None
    business_id: str | None = None
    environment: str | None = None
    idempotency_key: str | None = None
    completed_at: datetime | None = None
    error_classification: str = Field(min_length=1)
    error_message: str = Field(min_length=1)


class ArtifactProducedCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_run_id: str | None = None
    command_id: str | None = None
    business_id: str | None = None
    environment: str | None = None
    idempotency_key: str | None = None
    completed_at: datetime | None = None
    artifact_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class RunLifecycleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    event_type: str
    status: RunStatus
    trigger_run_id: str | None = None
    artifact_id: str | None = None
    artifact_type: str | None = None
    error_classification: str | None = None
    error_message: str | None = None
