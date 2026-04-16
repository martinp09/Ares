from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import utc_now


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignMembershipStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    SUPPRESSED = "suppressed"
    EXITED = "exited"


class CampaignRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    name: str = Field(min_length=1)
    provider_name: str | None = None
    provider_campaign_id: str | None = None
    provider_workspace_id: str | None = None
    status: CampaignStatus = CampaignStatus.DRAFT
    campaign_schedule: dict[str, Any] = Field(default_factory=dict)
    pl_value: str | None = None
    is_evergreen: bool = False
    sequences: list[dict[str, Any]] = Field(default_factory=list)
    email_gap: int | None = Field(default=None, ge=0)
    random_wait_max: int | None = Field(default=None, ge=0)
    text_only: bool = False
    first_email_text_only: bool = False
    email_list: list[str] = Field(default_factory=list)
    daily_limit: int | None = Field(default=None, ge=0)
    stop_on_reply: bool = True
    email_tag_list: list[str] = Field(default_factory=list)
    link_tracking: bool = True
    open_tracking: bool = True
    stop_on_auto_reply: bool = True
    daily_max_leads: int | None = Field(default=None, ge=0)
    prioritize_new_leads: bool = False
    auto_variant_select: bool = False
    match_lead_esp: bool = False
    stop_for_company: bool = False
    insert_unsubscribe_header: bool = True
    allow_risky_contacts: bool = False
    disable_bounce_protect: bool = False
    limit_emails_per_company_override: int | None = Field(default=None, ge=0)
    cc_list: list[str] = Field(default_factory=list)
    bcc_list: list[str] = Field(default_factory=list)
    owned_by: str | None = None
    ai_sdr_id: str | None = None
    provider_routing_rules: list[dict[str, Any]] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> str:
        if self.provider_campaign_id:
            provider = (self.provider_name or "provider").strip().casefold()
            return f"provider:{provider}:{self.provider_campaign_id.strip().casefold()}"
        return f"name:{self.name.strip().casefold()}"


class CampaignMembershipRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    lead_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    provider_membership_id: str | None = None
    provider_lead_id: str | None = None
    assigned_to: str | None = None
    status: CampaignMembershipStatus = CampaignMembershipStatus.PENDING
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    subscribed_at: datetime = Field(default_factory=utc_now)
    unsubscribed_at: datetime | None = None
    last_synced_at: datetime | None = None

    def replay_key(self) -> str:
        if self.idempotency_key:
            return self.idempotency_key
        return f"{self.campaign_id}:{self.lead_id}"
