from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class VoiceOutboundCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1, max_length=120)
    environment: str = Field(min_length=1, max_length=80)
    crm_record_id: str | None = Field(default=None, max_length=160)
    opportunity_id: str | None = Field(default=None, max_length=160)
    task_id: str | None = Field(default=None, max_length=160)
    to_number: str = Field(default="", max_length=40)
    from_number: str | None = Field(default=None, max_length=40)
    assistant_id: str | None = Field(default=None, max_length=160)
    phone_number_id: str | None = Field(default=None, max_length=160)
    customer_name: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)
    sync_hash: str | None = Field(default=None, max_length=240)
    dry_run: bool = True
    operator_approval: bool = False


class VoiceOutboundCallResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["vapi"] = "vapi"
    dry_run: bool
    would_call_provider: bool
    live_applied: bool
    action: str
    call_id: str | None = None
    provider_call_id: str | None = None
    provider_link_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None = None


class VoiceProviderListPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["vapi"] = "vapi"
    resource: Literal["assistants", "phone_numbers"]
    dry_run: bool = True
    would_call_provider: bool = False
    configured: bool
    default_id: str | None = None
    live_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)


class VoiceVapiWebhookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    event_type: str | None = None
    provider_call_id: str | None = None
    idempotency_key: str | None = None
    trust_status: str
    status: str | None = None
