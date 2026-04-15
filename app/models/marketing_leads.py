from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id, utc_now

BookingStatus = Literal["pending", "booked", "rescheduled", "cancelled"]


class LeadUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    email: str | None = None
    property_address: str = Field(min_length=1)
    booking_status: BookingStatus = "pending"


class MarketingLeadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("ctc"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    email: str | None = None
    property_address: str = Field(min_length=1)
    booking_status: BookingStatus = "pending"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
