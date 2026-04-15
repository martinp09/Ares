from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id, utc_now


class SequenceEnrollmentStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class SequenceEnrollmentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("seq"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    contact_id: str = Field(min_length=1)
    sequence_key: str = Field(min_length=1)
    status: SequenceEnrollmentStatus = SequenceEnrollmentStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
