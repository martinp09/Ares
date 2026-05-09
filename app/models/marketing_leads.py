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
    last_name: str | None = None
    property_type: str | None = None
    timeline_to_sell: str | None = None
    monthly_payment_goal: str | None = None
    asking_price_goal: str | None = None
    seller_goal: str | None = None
    notes: str | None = None
    sms_consent: bool = False
    consent_page_url: str | None = None
    consent_ip: str | None = None
    consent_user_agent: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    lp_var: str | None = None


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
    last_name: str | None = None
    property_type: str | None = None
    timeline_to_sell: str | None = None
    monthly_payment_goal: str | None = None
    asking_price_goal: str | None = None
    seller_goal: str | None = None
    notes: str | None = None
    sms_consent: bool = False
    consent_page_url: str | None = None
    consent_ip: str | None = None
    consent_user_agent: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    lp_var: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
