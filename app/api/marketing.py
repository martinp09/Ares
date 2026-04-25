from typing import Any

import inspect
from urllib.parse import parse_qs

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.services.booking_service import (
    LeaseOptionSequenceGuardRequest,
    ManualCallTaskRequest,
    NonBookerCheckRequest,
    booking_service,
)
from app.services.inbound_sms_service import LeaseOptionSequenceStepRequest, inbound_sms_service
from app.services.marketing_lead_service import LeadIntakePayload, marketing_lead_service

router = APIRouter(prefix="/marketing", tags=["marketing"])


class LeadIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    email: str | None = None
    property_address: str = Field(min_length=1)


class LeadIntakeResponse(BaseModel):
    lead_id: str
    booking_status: str
    booking_url: str


class BookingWebhookResponse(BaseModel):
    status: str
    lead_id: str
    booking_status: str


class SmsWebhookResponse(BaseModel):
    status: str
    event_type: str
    action: str


class NonBookerCheckResponse(BaseModel):
    bookingStatus: str
    shouldEnrollInSequence: bool
    startDay: int | None = None


class NonBookerCheckRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leadId: str = Field(min_length=1)
    businessId: str = Field(min_length=1)
    environment: str = Field(min_length=1)


class LeaseOptionSequenceGuardRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leadId: str = Field(min_length=1)
    businessId: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    day: int = Field(ge=0)


class LeaseOptionSequenceGuardResponse(BaseModel):
    bookingStatus: str
    sequenceStatus: str
    optedOut: bool


class LeaseOptionSequenceStepRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leadId: str = Field(min_length=1)
    businessId: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    day: int = Field(ge=0)
    channel: str = Field(min_length=1)
    templateId: str = Field(min_length=1)
    manualCallCheckpoint: bool = False


class LeaseOptionSequenceStepResponse(BaseModel):
    messageId: str
    channel: str
    status: str


class ManualCallTaskRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leadId: str = Field(min_length=1)
    businessId: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    sequenceDay: int = Field(ge=0)
    reason: str = Field(min_length=1)


class ManualCallTaskResponse(BaseModel):
    taskId: str
    status: str


class GenericWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")


@router.post("/leads", response_model=LeadIntakeResponse, status_code=status.HTTP_201_CREATED)
def create_marketing_lead(request: LeadIntakeRequest) -> LeadIntakeResponse:
    result = marketing_lead_service.intake_lead(
        LeadIntakePayload(
            business_id=request.business_id,
            environment=request.environment,
            first_name=request.first_name,
            phone=request.phone,
            email=request.email,
            property_address=request.property_address,
        )
    )
    return LeadIntakeResponse(**result)


@router.post("/webhooks/calcom", response_model=BookingWebhookResponse)
async def handle_calcom_webhook(
    request: Request,
    x_cal_signature: str | None = Header(default=None),
) -> BookingWebhookResponse:
    raw_body = await request.body()
    payload = await request.json()
    handler = booking_service.handle_calcom_webhook
    signature_params = inspect.signature(handler).parameters
    kwargs: dict[str, Any] = {"signature": x_cal_signature}
    if "raw_body" in signature_params:
        kwargs["raw_body"] = raw_body
    if "request_url" in signature_params:
        kwargs["request_url"] = str(request.url)
    if "request_headers" in signature_params:
        kwargs["request_headers"] = dict(request.headers)
    if "provider_event_id" in signature_params:
        kwargs["provider_event_id"] = request.headers.get("x-cal-event-id")
    if "idempotency_key" in signature_params:
        kwargs["idempotency_key"] = (
            request.headers.get("x-cal-event-id")
            or request.headers.get("x-cal-request-id")
            or request.headers.get("x-request-id")
        )
    try:
        result = handler(payload, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return BookingWebhookResponse(**result)


@router.post("/webhooks/textgrid", response_model=SmsWebhookResponse)
async def handle_textgrid_webhook(
    request: Request,
    x_textgrid_signature: str | None = Header(default=None),
) -> SmsWebhookResponse:
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
    kwargs: dict[str, Any] = {"signature": x_textgrid_signature}
    signature_params = inspect.signature(handler).parameters
    if "request_url" in signature_params:
        kwargs["request_url"] = str(request.url)
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return SmsWebhookResponse(**result)


@router.post("/internal/non-booker-check", response_model=NonBookerCheckResponse)
def run_non_booker_check(request: NonBookerCheckRequestModel) -> NonBookerCheckResponse:
    result = booking_service.run_non_booker_check(
        NonBookerCheckRequest(
            lead_id=request.leadId,
            business_id=request.businessId,
            environment=request.environment,
        )
    )
    return NonBookerCheckResponse(
        bookingStatus=str(result["booking_status"]),
        shouldEnrollInSequence=bool(result["should_enroll_in_sequence"]),
        startDay=int(result["start_day"]) if result.get("start_day") is not None else None,
    )


@router.post("/internal/lease-option-sequence/guard", response_model=LeaseOptionSequenceGuardResponse)
def lease_option_sequence_guard(request: LeaseOptionSequenceGuardRequestModel) -> LeaseOptionSequenceGuardResponse:
    result = booking_service.get_lease_option_sequence_guard(
        LeaseOptionSequenceGuardRequest(
            lead_id=request.leadId,
            business_id=request.businessId,
            environment=request.environment,
            day=request.day,
        )
    )
    return LeaseOptionSequenceGuardResponse(
        bookingStatus=str(result["booking_status"]),
        sequenceStatus=str(result["sequence_status"]),
        optedOut=bool(result["opted_out"]),
    )


@router.post("/internal/lease-option-sequence/step", response_model=LeaseOptionSequenceStepResponse)
def lease_option_sequence_step(request: LeaseOptionSequenceStepRequestModel) -> LeaseOptionSequenceStepResponse:
    result = inbound_sms_service.dispatch_lease_option_sequence_step(
        LeaseOptionSequenceStepRequest(
            lead_id=request.leadId,
            business_id=request.businessId,
            environment=request.environment,
            day=request.day,
            channel=request.channel,
            template_id=request.templateId,
            manual_call_checkpoint=request.manualCallCheckpoint,
        )
    )
    return LeaseOptionSequenceStepResponse(
        messageId=str(result["message_id"]),
        channel=str(result["channel"]),
        status=str(result["status"]),
    )


@router.post("/internal/manual-call-task", response_model=ManualCallTaskResponse)
def create_manual_call_task(request: ManualCallTaskRequestModel) -> ManualCallTaskResponse:
    result = booking_service.create_manual_call_task(
        ManualCallTaskRequest(
            lead_id=request.leadId,
            business_id=request.businessId,
            environment=request.environment,
            sequence_day=request.sequenceDay,
            reason=request.reason,
        )
    )
    return ManualCallTaskResponse(taskId=str(result["task_id"]), status=str(result["status"]))
