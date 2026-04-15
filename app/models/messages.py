from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id, utc_now


class MessageDirection(StrEnum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class MessageStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"
    RECEIVED = "received"


class MessageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("msg"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    contact_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    direction: MessageDirection
    provider: str | None = None
    external_message_id: str | None = None
    subject: str | None = None
    body: str = Field(min_length=1)
    status: MessageStatus
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
