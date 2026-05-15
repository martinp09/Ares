from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.models.calls import (
    VoiceOutboundCallRequest,
    VoiceOutboundCallResponse,
    VoiceProviderListPreviewResponse,
    VoiceVapiWebhookResponse,
)
from app.services.vapi_call_service import VapiCallService

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/assistants", response_model=VoiceProviderListPreviewResponse, response_model_exclude_none=True)
def list_vapi_assistants() -> VoiceProviderListPreviewResponse:
    return VoiceProviderListPreviewResponse(**VapiCallService().list_assistants_preview())


@router.get("/phone-numbers", response_model=VoiceProviderListPreviewResponse, response_model_exclude_none=True)
def list_vapi_phone_numbers() -> VoiceProviderListPreviewResponse:
    return VoiceProviderListPreviewResponse(**VapiCallService().list_phone_numbers_preview())


@router.post("/calls/outbound", response_model=VoiceOutboundCallResponse, response_model_exclude_none=True)
def create_outbound_call(payload: VoiceOutboundCallRequest) -> VoiceOutboundCallResponse:
    try:
        service = VapiCallService()
        result = service.preview_outbound_call(payload) if payload.dry_run else service.dispatch_outbound_call(payload)
        return VoiceOutboundCallResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/vapi/webhook", response_model=VoiceVapiWebhookResponse, response_model_exclude_none=True)
async def handle_vapi_webhook(request: Request, x_vapi_secret: str | None = Header(default=None)) -> VoiceVapiWebhookResponse:
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="Invalid JSON webhook payload") from exc
    headers = dict(request.headers)
    if x_vapi_secret is not None:
        headers["x-vapi-secret"] = x_vapi_secret
    return VoiceVapiWebhookResponse(**VapiCallService().handle_webhook(payload, headers))
