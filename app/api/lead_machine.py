from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import get_settings
from app.services.probate_write_path_service import ProbateWritePathService, probate_write_path_service

router = APIRouter(prefix="/lead-machine", tags=["lead-machine"])


class ProbateIntakeRecordInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    case_number: str | None = None
    cause_number: str | None = None
    filing_type: str | None = None
    type: str | None = None
    hcad_candidates: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_required_aliases(self) -> "ProbateIntakeRecordInput":
        if not ((self.case_number and self.case_number.strip()) or (self.cause_number and self.cause_number.strip())):
            raise ValueError("case_number or cause_number is required")
        if not ((self.filing_type and self.filing_type.strip()) or (self.type and self.type.strip())):
            raise ValueError("filing_type or type is required")
        return self


class ProbateIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    records: list[ProbateIntakeRecordInput] = Field(min_length=1)
    keep_only: bool = True


class ProbateIntakeRecordResult(BaseModel):
    case_number: str
    keep_now: bool
    lead_score: float | None = None
    hcad_match_status: str
    contact_confidence: str
    bridged_lead_id: str | None = None


class ProbateIntakeResponse(BaseModel):
    processed_count: int
    keep_now_count: int
    bridged_count: int
    records: list[ProbateIntakeRecordResult]


class OutboundEnqueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    lead_ids: list[str] = Field(min_length=1)
    campaign_id: str | None = None
    list_id: str | None = None
    skip_if_in_workspace: bool = True
    skip_if_in_campaign: bool = True
    skip_if_in_list: bool = True
    blocklist_id: str | None = None
    assigned_to: str | None = None
    verify_leads_on_import: bool = False
    chunk_size: int | None = Field(default=None, ge=1, le=1000)
    wait_seconds: float | None = Field(default=None, ge=0)


class OutboundEnqueueResponse(BaseModel):
    automation_run_ids: list[str]
    membership_ids: list[str]
    suppressed_lead_ids: list[str]
    provider_batches: list[dict[str, Any]]


class InstantlyWebhookResponse(BaseModel):
    status: str
    receipt_id: str
    event_id: str | None = None
    lead_id: str | None = None
    suppression_id: str | None = None
    membership_id: str | None = None
    task_id: str | None = None


class InstantlyWebhookRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    payload: dict[str, Any]
    trusted: bool = False
    trust_reason: str | None = None


def _build_write_path_service() -> ProbateWritePathService:
    return probate_write_path_service


@router.post("/probate/intake", response_model=ProbateIntakeResponse, status_code=status.HTTP_201_CREATED)
def intake_probate_records(request: ProbateIntakeRequest) -> ProbateIntakeResponse:
    service = _build_write_path_service()
    result = service.intake_probate_cases(
        business_id=request.business_id,
        environment=request.environment,
        payloads=[record.model_dump(mode="python", exclude_none=True) for record in request.records],
        keep_only=request.keep_only,
    )

    return ProbateIntakeResponse(
        processed_count=result["processed_count"],
        keep_now_count=result["keep_now_count"],
        bridged_count=result["bridged_count"],
        records=[ProbateIntakeRecordResult(**record) for record in result["records"]],
    )


@router.post("/outbound/enqueue", response_model=OutboundEnqueueResponse)
def enqueue_outbound_leads(request: OutboundEnqueueRequest) -> OutboundEnqueueResponse:
    try:
        service = _build_write_path_service()
        result = service.enqueue_probate_leads(
            business_id=request.business_id,
            environment=request.environment,
            lead_ids=request.lead_ids,
            campaign_id=request.campaign_id,
            list_id=request.list_id,
            skip_if_in_workspace=request.skip_if_in_workspace,
            skip_if_in_campaign=request.skip_if_in_campaign,
            skip_if_in_list=request.skip_if_in_list,
            blocklist_id=request.blocklist_id,
            assigned_to=request.assigned_to,
            verify_leads_on_import=request.verify_leads_on_import,
            chunk_size=request.chunk_size,
            wait_seconds=request.wait_seconds,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lead not found: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return OutboundEnqueueResponse(
        automation_run_ids=[run.id for run in result.automation_runs if run.id],
        membership_ids=[membership.id for membership in result.memberships if membership.id],
        suppressed_lead_ids=result.suppressed_lead_ids,
        provider_batches=result.provider_batches,
    )


@router.post("/webhooks/instantly", response_model=InstantlyWebhookResponse)
async def ingest_instantly_webhook(
    request: Request,
    body: InstantlyWebhookRequest,
    x_instantly_signature: str | None = Header(default=None),
) -> InstantlyWebhookResponse:
    settings = get_settings()
    trusted = body.trusted
    trust_reason = body.trust_reason
    if not isinstance(trust_reason, str) or not trust_reason.strip():
        if x_instantly_signature:
            trust_reason = "signature_present_unverified"
        elif settings.instantly_webhook_secret:
            trust_reason = "secret_configured_signature_missing"
        else:
            trust_reason = "signature_verification_not_configured"

    result = _build_write_path_service().handle_instantly_webhook(
        business_id=body.business_id,
        environment=body.environment,
        payload=body.payload,
        headers=dict(request.headers),
        trusted=trusted,
        trust_reason=str(trust_reason),
    )
    return InstantlyWebhookResponse(**result)
