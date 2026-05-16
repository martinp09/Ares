from __future__ import annotations

import inspect
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, Response, status

from app.models.sms_agent import (
    SmsAgentProcessPendingRequest,
    SmsAgentProcessPendingResponse,
    SmsAgentSendRequest,
    SmsAgentSendResponse,
)
from app.services.inbound_sms_service import inbound_sms_service
from app.services.sms_agent_service import SmsAgentService

router = APIRouter(prefix="/sms-agent", tags=["sms-agent"])
public_router = APIRouter(prefix="/sms-agent", tags=["sms-agent"])


def sms_agent_service_dependency() -> SmsAgentService:
    return SmsAgentService()


@router.post("/messages", response_model=SmsAgentSendResponse, status_code=status.HTTP_201_CREATED)
def send_sms_agent_message(
    request: SmsAgentSendRequest,
    service: SmsAgentService = Depends(sms_agent_service_dependency),
) -> SmsAgentSendResponse:
    try:
        return service.send_message(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/internal/process-pending", response_model=SmsAgentProcessPendingResponse)
def process_pending_sms_agent_jobs(
    request: SmsAgentProcessPendingRequest = Body(default_factory=SmsAgentProcessPendingRequest),
    service: SmsAgentService = Depends(sms_agent_service_dependency),
) -> SmsAgentProcessPendingResponse:
    return SmsAgentProcessPendingResponse(**service.process_pending(limit=request.limit))


@public_router.post("/webhooks/textgrid")
async def handle_textgrid_sms_agent_webhook(
    request: Request,
    x_textgrid_signature: str | None = Header(default=None),
    x_twilio_signature: str | None = Header(default=None),
) -> Response:
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/x-www-form-urlencoded"):
        payload = {
            key: values[-1]
            for key, values in parse_qs(raw_body.decode("utf-8"), keep_blank_values=True).items()
        }
    elif content_type.startswith("multipart/form-data"):
        payload = dict(await request.form())
    else:
        payload = await request.json()

    handler = inbound_sms_service.handle_textgrid_webhook
    kwargs: dict[str, Any] = {
        "signature": x_textgrid_signature or x_twilio_signature,
        "request_url": str(request.url),
    }
    signature_params = inspect.signature(handler).parameters
    if "raw_body" in signature_params:
        kwargs["raw_body"] = raw_body
    if "request_headers" in signature_params:
        kwargs["request_headers"] = dict(request.headers)
    if "provider_event_id" in signature_params:
        kwargs["provider_event_id"] = (
            request.headers.get("x-textgrid-event-id")
            or request.headers.get("x-textgrid-message-id")
        )
    if "idempotency_key" in signature_params:
        kwargs["idempotency_key"] = (
            request.headers.get("x-textgrid-event-id")
            or request.headers.get("x-textgrid-message-id")
            or request.headers.get("x-request-id")
        )
    try:
        result = handler(payload, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return Response(
        "<Response></Response>",
        media_type="application/xml",
        headers={"X-Ares-Sms-Agent-Status": str(result.get("status") or "processed")},
    )
