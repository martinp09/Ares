from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import Settings
from app.core.dependencies import settings_dependency
from app.models.voice_agents import (
    VapiWebhookResponse,
    VoiceAssistantCreateRequest,
    VoiceOutboundCallRequest,
    VoicePhoneNumberCreateRequest,
    VoiceProviderActionResponse,
)
from app.services.voice_agent_service import VoiceAgentService

router = APIRouter(prefix="/voice", tags=["voice"])


def voice_agent_service_dependency() -> VoiceAgentService:
    return VoiceAgentService()


def _validate_vapi_webhook_secret(settings: Settings, provided_secret: str | None) -> None:
    if not settings.provider_webhook_signatures_required:
        return
    if not settings.vapi_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vapi webhook secret is required",
        )
    if not provided_secret or not hmac.compare_digest(str(settings.vapi_webhook_secret), provided_secret):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid Vapi webhook secret",
        )


@router.post("/assistants", response_model=VoiceProviderActionResponse, status_code=status.HTTP_201_CREATED)
def create_voice_assistant(
    request: VoiceAssistantCreateRequest,
    service: VoiceAgentService = Depends(voice_agent_service_dependency),
) -> VoiceProviderActionResponse:
    try:
        return service.create_assistant(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/phone-numbers", response_model=VoiceProviderActionResponse, status_code=status.HTTP_201_CREATED)
def create_voice_phone_number(
    request: VoicePhoneNumberCreateRequest,
    service: VoiceAgentService = Depends(voice_agent_service_dependency),
) -> VoiceProviderActionResponse:
    try:
        return service.create_phone_number(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/calls/outbound", response_model=VoiceProviderActionResponse, status_code=status.HTTP_201_CREATED)
def create_voice_outbound_call(
    request: VoiceOutboundCallRequest,
    service: VoiceAgentService = Depends(voice_agent_service_dependency),
) -> VoiceProviderActionResponse:
    try:
        return service.create_outbound_call(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/vapi/webhook", response_model=VapiWebhookResponse)
def handle_vapi_webhook(
    payload: dict[str, Any],
    x_vapi_secret: str | None = Header(default=None),
    settings: Settings = Depends(settings_dependency),
    service: VoiceAgentService = Depends(voice_agent_service_dependency),
) -> VapiWebhookResponse:
    _validate_vapi_webhook_secret(settings, x_vapi_secret)
    return service.handle_webhook(payload)
