from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProviderExtrasStatus = Literal["configuration_missing", "scaffolded", "projected"]
ProviderExtrasProjectionMode = Literal["internal_projection", "settings_only", "scaffold"]


class ProviderExtraFamilyStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported: bool = True
    configured: bool
    live_provider_wired: bool = False
    status: ProviderExtrasStatus
    projection_mode: ProviderExtrasProjectionMode
    projected_record_count: int = Field(default=0, ge=0)
    counts: dict[str, int] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ProviderExtrasSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family_count: int = Field(default=8, ge=0)
    configured_family_count: int = Field(ge=0)
    projected_family_count: int = Field(ge=0)
    campaign_count: int = Field(ge=0)
    lead_count: int = Field(ge=0)
    workspace_count: int = Field(ge=0)
    webhook_receipt_count: int = Field(ge=0)
    blocklist_count: int = Field(ge=0)


class InstantlyProviderExtrasSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["instantly"] = "instantly"
    configured: bool
    transport_ready: bool
    webhook_signing_configured: bool
    live_provider_wired: bool = False
    integration_mode: Literal["backend_only_projection"] = "backend_only_projection"
    base_url: str = Field(min_length=1)
    batch_size: int = Field(ge=1)
    batch_wait_seconds: float = Field(ge=0)
    summary: ProviderExtrasSummary
    labels: ProviderExtraFamilyStatus
    tags: ProviderExtraFamilyStatus
    verification: ProviderExtraFamilyStatus
    deliverability: ProviderExtraFamilyStatus
    blocklists: ProviderExtraFamilyStatus
    inbox_placement: ProviderExtraFamilyStatus
    crm_actions: ProviderExtraFamilyStatus
    workspace_resources: ProviderExtraFamilyStatus
    checked_at: datetime
