from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id, utc_now

BookingEventType = Literal["booked", "rescheduled", "cancelled"]


class BookingEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("bkg"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    contact_id: str = Field(min_length=1)
    conversation_id: str | None = None
    event_type: BookingEventType
    provider: str = Field(min_length=1)
    external_booking_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
