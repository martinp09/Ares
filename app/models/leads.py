from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import utc_now


class LeadSource(StrEnum):
    MANUAL = "manual"
    PROBATE_INTAKE = "probate_intake"
    INSTANTLY_IMPORT = "instantly_import"
    INSTANTLY_SYNC = "instantly_sync"


class LeadLifecycleStatus(StrEnum):
    NEW = "new"
    READY = "ready"
    ROUTED = "routed"
    ACTIVE = "active"
    SUPPRESSED = "suppressed"
    CLOSED = "closed"


class LeadInterestStatus(StrEnum):
    NEUTRAL = "neutral"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    MEETING_BOOKED = "meeting_booked"
    MEETING_COMPLETED = "meeting_completed"
    CLOSED = "closed"
    OUT_OF_OFFICE = "out_of_office"
    WRONG_PERSON = "wrong_person"
    AUTO_REPLY = "auto_reply"
    UNSUBSCRIBED = "unsubscribed"


class LeadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    source: LeadSource = LeadSource.MANUAL
    lifecycle_status: LeadLifecycleStatus = LeadLifecycleStatus.NEW
    provider_name: str | None = None
    provider_lead_id: str | None = None
    provider_workspace_id: str | None = None
    external_key: str | None = None
    campaign_id: str | None = None
    list_id: str | None = None
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    website: str | None = None
    job_title: str | None = None
    mailing_address: str | None = None
    property_address: str | None = None
    probate_case_number: str | None = None
    personalization: dict[str, Any] = Field(default_factory=dict)
    custom_variables: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None
    lt_interest_status: LeadInterestStatus = LeadInterestStatus.NEUTRAL
    pl_value_lead: str | None = None
    assigned_to: str | None = None
    verification_status: str | None = None
    enrichment_status: str | None = None
    upload_method: str | None = None
    is_website_visitor: bool = False
    esp_code: str | None = None
    esg_code: str | None = None
    status_summary: str | None = None
    status_summary_subseq: str | None = None
    last_step: str | None = None
    last_step_variant: str | None = None
    open_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)
    click_count: int = Field(default=0, ge=0)
    email_opened_at: datetime | None = None
    email_replied_at: datetime | None = None
    email_clicked_at: datetime | None = None
    last_contacted_at: datetime | None = None
    last_interest_changed_at: datetime | None = None
    last_touched_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> str:
        if self.external_key:
            return f"external:{self.external_key.strip().casefold()}"
        if self.provider_lead_id:
            provider = (self.provider_name or "provider").strip().casefold()
            return f"provider:{provider}:{self.provider_lead_id.strip().casefold()}"
        if self.email:
            return f"email:{self.email.strip().casefold()}"
        if self.phone:
            return f"phone:{''.join(self.phone.split())}"
        raise ValueError("LeadRecord requires external_key, provider_lead_id, email, or phone for deterministic identity")
