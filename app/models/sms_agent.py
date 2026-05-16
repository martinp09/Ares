from __future__ import annotations

from datetime import datetime
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


class SmsAgentProcessPendingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    limit: int | None = Field(default=None, ge=1, le=100)


class SmsAgentProcessPendingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    processed_count: int
    sent_count: int
    blocked_count: int
    failed_count: int


class SmsAgentJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    provider_webhook_id: str | None = None
    message_id: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None
    from_number: str = Field(min_length=1)
    to_number: str = Field(min_length=1)
    payload_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmsAgentJobRecord(SmsAgentJobCreate):
    id: str = Field(min_length=1)
    status: str = "pending"
    attempt_count: int = 0
    locked_until: datetime | None = None
    decision_id: str | None = None
    last_error: str | None = None
    deduped: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SmsAgentReplyDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    message_id: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None
    intent: str = Field(min_length=1)
    source_lane: str = Field(min_length=1)
    temperature: str = Field(min_length=1)
    urgency: str = Field(min_length=1)
    action: str = Field(min_length=1)
    suggested_body: str | None = None
    confidence: float = Field(ge=0, le=1)
    policy_reason: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    provider_kind: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmsAgentReplyDecisionRecord(SmsAgentReplyDecisionCreate):
    id: str = Field(min_length=1)
    created_at: datetime | None = None
