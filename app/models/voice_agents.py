from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VoiceAssistantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Ares RE Lead Desk", min_length=1)
    first_message: str = Field(
        default="Hi, this is the Ares real estate desk. I can help route your property situation and get the right follow-up started. What can I help with today?",
        min_length=1,
    )
    system_prompt: str | None = Field(default=None, min_length=1)
    server_url: str | None = None
    model_provider: str | None = None
    model: str | None = None
    voice_provider: str | None = None
    voice_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    dry_run_only: bool = False


class VoicePhoneNumberCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Ares Voice Agent Number", min_length=1)
    assistant_id: str | None = Field(default=None, min_length=1)
    number_desired_area_code: str | None = Field(default=None, min_length=3)
    server_url: str | None = None
    dry_run_only: bool = False


class VoiceOutboundCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: str = Field(min_length=1)
    assistant_id: str | None = Field(default=None, min_length=1)
    phone_number_id: str | None = Field(default=None, min_length=1)
    first_message: str | None = Field(default=None, min_length=1)
    system_prompt: str | None = Field(default=None, min_length=1)
    earliest_at: str | None = None
    latest_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    dry_run_only: bool = False


class VoiceProviderActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "vapi"
    action: str
    status: str
    dry_run: bool
    provider_id: str | None = None
    request_payload: dict[str, Any]
    provider_response: dict[str, Any] | None = None
    error_message: str | None = None


class VapiWebhookResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None
    event_type: str | None = None
    assistantId: str | None = None
    assistant: dict[str, Any] | None = None
    destination: dict[str, Any] | None = None
    error: str | None = None
    results: list[dict[str, Any]] | None = None
