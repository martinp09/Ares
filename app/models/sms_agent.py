from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SmsAgentSendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    to: str = Field(min_length=1)
    body: str = Field(min_length=1)
    contact_id: str | None = Field(default=None, min_length=1)
    conversation_id: str | None = Field(default=None, min_length=1)
    sms_consent_confirmed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    dry_run_only: bool = False


class SmsAgentSendResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["sms"] = "sms"
    provider: Literal["textgrid"] = "textgrid"
    status: str
    to: str
    from_identity: str | None = None
    message_id: str | None = None
    conversation_id: str | None = None
    provider_message_id: str | None = None
    dry_run: bool
    log_status: str
    error_message: str | None = None


class SmsAgentWebhookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    event_type: str
    action: str
    message_id: str | None = None
    task_id: str | None = None
