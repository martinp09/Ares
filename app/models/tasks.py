from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import utc_now


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskType(StrEnum):
    MANUAL_CALL = "manual_call"
    MANUAL_REVIEW = "manual_review"
    FOLLOW_UP = "follow_up"
    SUPPRESSION_REVIEW = "suppression_review"
    DATA_ENRICHMENT = "data_enrichment"


class TaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: TaskStatus
    task_type: TaskType = TaskType.MANUAL_CALL
    priority: TaskPriority = TaskPriority.NORMAL
    run_id: str | None = None
    lead_id: str | None = None
    automation_run_id: str | None = None
    source_event_id: str | None = None
    due_at: datetime | None = None
    assigned_to: str | None = None
    idempotency_key: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    deduped: bool = False
