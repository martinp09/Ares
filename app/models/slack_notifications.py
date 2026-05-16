from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id, utc_now


class SlackNotificationRoute(StrEnum):
    LEAD_RUNS = "lead_runs"
    HOT_LEADS = "hot_leads"
    INSTANTLY_REPLIES = "instantly_replies"
    LEASE_OPTION_INBOUND = "lease_option_inbound"
    SMS_CALLS = "sms_calls"
    ERRORS = "errors"


SlackNotificationStatus = Literal["skipped", "sent", "failed"]


class SlackNotificationAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("slack_notice"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    route: SlackNotificationRoute
    dedupe_key: str = Field(min_length=1)
    channel_id: str | None = None
    status: SlackNotificationStatus
    slack_message_ts: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    sent_at: str | None = None
    deduped: bool = False
