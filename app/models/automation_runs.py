from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import utc_now


class AutomationRunStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutomationRunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    workflow_name: str = Field(min_length=1)
    workflow_version: str | None = None
    workflow_step: str | None = None
    phase: str | None = None
    lead_id: str | None = None
    campaign_id: str | None = None
    source_event_id: str | None = None
    parent_run_id: str | None = None
    trigger_run_id: str | None = None
    provider_run_id: str | None = None
    status: AutomationRunStatus = AutomationRunStatus.QUEUED
    idempotency_key: str = Field(min_length=1)
    replay_key: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_classification: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    deduped: bool = False

    def replay_safe_key(self) -> str:
        return self.replay_key or self.idempotency_key
