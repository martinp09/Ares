from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import utc_now


class LeadEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    lead_id: str = Field(min_length=1)
    campaign_id: str | None = None
    automation_run_id: str | None = None
    provider_name: str | None = None
    provider_event_id: str | None = None
    provider_receipt_id: str | None = None
    source_event_id: str | None = None
    event_type: str = Field(min_length=1)
    event_timestamp: datetime = Field(default_factory=utc_now)
    received_at: datetime = Field(default_factory=utc_now)
    idempotency_key: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    deduped: bool = False

    def replay_key(self) -> str:
        return self.idempotency_key


class ProviderWebhookReceiptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    provider_event_id: str | None = None
    provider_receipt_id: str | None = None
    lead_email: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=utc_now)
    processed: bool = False
    processed_at: datetime | None = None
    lead_event_id: str | None = None
    deduped: bool = False

    def replay_key(self) -> str:
        provider = self.provider.strip().casefold()
        return f"{provider}:{self.idempotency_key}"
