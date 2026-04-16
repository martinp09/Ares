from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import utc_now


class SuppressionScope(StrEnum):
    GLOBAL = "global"
    CAMPAIGN = "campaign"


class SuppressionSource(StrEnum):
    MANUAL = "manual"
    PROVIDER = "provider"
    WEBHOOK = "webhook"
    AUTOMATION = "automation"
    IMPORT = "import"


class SuppressionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    lead_id: str | None = None
    email: str | None = None
    phone: str | None = None
    campaign_id: str | None = None
    provider_blocklist_id: str | None = None
    scope: SuppressionScope = SuppressionScope.GLOBAL
    reason: str = Field(min_length=1)
    source: SuppressionSource = SuppressionSource.MANUAL
    active: bool = True
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    archived_at: datetime | None = None

    def scope_key(self) -> str:
        target = self.lead_id or (self.email.strip().casefold() if self.email else None) or self.phone
        if target is None:
            raise ValueError("SuppressionRecord requires lead_id, email, or phone for deterministic scope")
        if self.scope == SuppressionScope.CAMPAIGN:
            if self.campaign_id is None:
                raise ValueError("Campaign-scoped suppression requires campaign_id")
            return f"campaign:{self.campaign_id}:{target}"
        return f"global:{target}"
