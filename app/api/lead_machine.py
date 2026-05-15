from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import get_settings
from app.db.tasks import TasksRepository
from app.models.commands import utc_now
from app.models.lead_events import LeadEventRecord
from app.models.source_runs import MorningBrief, MorningBriefRequest, NightlySourcePullRequest, NightlySourcePullResponse
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType
from app.providers.instantly import verify_webhook_signature
from app.services.harris_daily_lead_machine_service import (
    HarrisDailyLeadMachineService,
    harris_daily_lead_machine_service,
)
from app.services.inbound_sms_service import LeaseOptionSequenceStepRequest, inbound_sms_service
from app.services.lead_intake_service import LeadIntakeRequest as ServiceLeadIntakeRequest
from app.services.lead_intake_service import lead_intake_service
from app.services.lead_sequence_runner import LeadSequenceRunner, lead_sequence_runner
from app.services.lead_suppression_service import LeadSuppressionService, lead_suppression_service
from app.services.nightly_lead_machine_service import nightly_lead_machine_service
from app.services.probate_property_tax_title_enrichment_service import ProbatePropertyTaxTitleEnrichmentService
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


class LeadMachineIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    source: str = Field(default="manual", min_length=1)
    source_record_id: str | None = None
    campaign_key: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    property_address: str | None = None
    county: str | None = None
    status: str = Field(default="new", min_length=1)
    pipeline_stage: str | None = None
    priority: str | None = None
    dedupe_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LeadMachineIntakeResponse(BaseModel):
    status: Literal["created", "deduped", "queued", "skipped"]
    lead_id: str
    event_id: str
    queued: bool
    skipped: bool
    failed_side_effects: list[str]


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


class HarrisDailyImportRecordInput(BaseModel):
    model_config = ConfigDict(extra="allow")


class HarrisDailyImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    run_date: date
    probate_records: list[HarrisDailyImportRecordInput] = Field(default_factory=list)
    hcad_estate_of_records: list[HarrisDailyImportRecordInput] = Field(default_factory=list)
    dry_run: bool = True
    keep_only: bool = True

    @model_validator(mode="after")
    def _validate_sources(self) -> "HarrisDailyImportRequest":
        if not self.probate_records and not self.hcad_estate_of_records:
            raise ValueError("probate_records or hcad_estate_of_records is required")
        return self


class ProbatePropertyTaxTitleEnrichmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    keep_now_rows: list[dict[str, Any]] = Field(default_factory=list)
    hcad_candidates_by_case: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    tax_overlays_by_case: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tax_overlays_by_account: dict[str, dict[str, Any]] = Field(default_factory=dict)
    land_record_rows_by_case: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    live_cad_calls: bool = False
    live_tax_calls: bool = False
    live_land_record_calls: bool = False
    enrichment_approval: dict[str, Any] = Field(default_factory=dict)


class ProbatePropertyTaxTitleEnrichmentResponse(BaseModel):
    business_id: str
    environment: str
    received_count: int
    enriched_count: int
    property_match_completed_count: int
    property_match_unmatched_count: int
    tax_overlay_completed_count: int
    tax_overlay_ambiguous_count: int
    title_friction_completed_count: int
    title_friction_review_count: int
    hubspot_mirror_blocked_until_approval_count: int
    outbound_blocked_until_explicit_approval_count: int
    no_send: bool
    provider_sends_enabled: bool
    outbound_allowed: bool
    live_cad_calls_attempted: bool
    live_tax_calls_attempted: bool
    live_land_record_calls_attempted: bool
    records: list[dict[str, Any]]


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
    operator_approval: bool = False


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


class FollowupStepRunnerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    lead_id: str = Field(min_length=1)
    day: int = Field(ge=0)
    channel: Literal["sms", "email"]
    template_id: str = Field(min_length=1)
    manual_call_checkpoint: bool = False
    campaign_id: str | None = None


class FollowupStepRunnerResponse(BaseModel):
    message_id: str
    channel: Literal["sms", "email"]
    status: str
    suppressed: bool


class SuppressionSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    lead_id: str = Field(min_length=1)
    campaign_id: str | None = None
    lead_email: str | None = None
    event_type: str = Field(min_length=1)
    provider_name: str | None = None
    provider_event_id: str | None = None
    event_timestamp: datetime | None = None
    idempotency_key: str | None = None


class SuppressionSyncResponse(BaseModel):
    status: str
    suppression_id: str | None = None
    reason: str | None = None
    active: bool
    event_type: str


class TaskReminderOrOverdueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    task_title: str = Field(min_length=1)
    due_at: datetime
    status: str = Field(min_length=1)
    lead_id: str | None = None
    assigned_to: str | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None


class TaskReminderOrOverdueResponse(BaseModel):
    status: str
    reminder_task_id: str | None = None
    overdue: bool
    reminder_created: bool


tasks_repository = TasksRepository()


def _build_write_path_service() -> ProbateWritePathService:
    return probate_write_path_service


def _build_daily_lead_machine_service() -> HarrisDailyLeadMachineService:
    return harris_daily_lead_machine_service


def _build_property_tax_title_enrichment_service() -> ProbatePropertyTaxTitleEnrichmentService:
    return ProbatePropertyTaxTitleEnrichmentService()


@router.post("/intake", response_model=LeadMachineIntakeResponse, status_code=status.HTTP_201_CREATED)
def intake_lead(request: LeadMachineIntakeRequest) -> LeadMachineIntakeResponse:
    try:
        result = lead_intake_service.intake_lead(
            ServiceLeadIntakeRequest(**request.model_dump(mode="python"))
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return LeadMachineIntakeResponse(
        status=result.status,
        lead_id=result.lead.id or "",
        event_id=result.intake_event.id or "",
        queued=result.queued,
        skipped=result.skipped,
        failed_side_effects=result.failed_side_effects,
    )


@router.post("/probate/intake", response_model=ProbateIntakeResponse, status_code=status.HTTP_201_CREATED)
def intake_probate_records(request: ProbateIntakeRequest) -> ProbateIntakeResponse:
    service = _build_write_path_service()
    payloads = [record.model_dump(mode="python", exclude_none=True) for record in request.records]
    hcad_candidates_by_case = {
        str(payload.get("case_number") or payload.get("cause_number") or "").strip(): payload.get("hcad_candidates") or []
        for payload in payloads
        if (payload.get("hcad_candidates") or [])
    }
    result = service.intake_probate_cases(
        business_id=request.business_id,
        environment=request.environment,
        payloads=payloads,
        hcad_candidates_by_case=hcad_candidates_by_case or None,
        keep_only=request.keep_only,
    )

    return ProbateIntakeResponse(
        processed_count=result["processed_count"],
        keep_now_count=result["keep_now_count"],
        bridged_count=result["bridged_count"],
        records=[ProbateIntakeRecordResult(**record) for record in result["records"]],
    )


@router.post("/harris/daily-import", status_code=status.HTTP_201_CREATED)
def import_harris_daily_leads(request: HarrisDailyImportRequest) -> dict[str, Any]:
    service = _build_daily_lead_machine_service()
    try:
        probate_payloads = [record.model_dump(mode="python", exclude_none=True) for record in request.probate_records]
        estate_payloads = [
            record.model_dump(mode="python", exclude_none=True) for record in request.hcad_estate_of_records
        ]
        return service.run_daily_import(
            business_id=request.business_id,
            environment=request.environment,
            run_date=request.run_date,
            probate_records=probate_payloads,
            hcad_estate_of_records=estate_payloads,
            dry_run=request.dry_run,
            keep_only=request.keep_only,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post(
    "/internal/probate-property-tax-title-enrichment",
    response_model=ProbatePropertyTaxTitleEnrichmentResponse,
)
def run_probate_property_tax_title_enrichment(
    request: ProbatePropertyTaxTitleEnrichmentRequest,
) -> ProbatePropertyTaxTitleEnrichmentResponse:
    try:
        result = _build_property_tax_title_enrichment_service().run_enrichment(
            business_id=request.business_id,
            environment=request.environment,
            keep_now_rows=request.keep_now_rows,
            hcad_candidates_by_case=request.hcad_candidates_by_case,
            tax_overlays_by_case=request.tax_overlays_by_case,
            tax_overlays_by_account=request.tax_overlays_by_account,
            land_record_rows_by_case=request.land_record_rows_by_case,
            live_cad_calls=request.live_cad_calls,
            live_tax_calls=request.live_tax_calls,
            live_land_record_calls=request.live_land_record_calls,
            enrichment_approval=request.enrichment_approval,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return ProbatePropertyTaxTitleEnrichmentResponse(**result)


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
            operator_approval=request.operator_approval,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lead not found: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return OutboundEnqueueResponse(
        automation_run_ids=[run.id for run in result.automation_runs if run.id],
        membership_ids=[membership.id for membership in result.memberships if membership.id],
        suppressed_lead_ids=result.suppressed_lead_ids,
        provider_batches=result.provider_batches,
    )


@router.post("/webhooks/instantly", response_model=InstantlyWebhookResponse)
async def ingest_instantly_webhook(
    request: Request,
    body: InstantlyWebhookRequest | dict[str, Any],
    business_id: str | None = Query(default=None, min_length=1),
    environment: str | None = Query(default=None, min_length=1),
    x_instantly_signature: str | None = Header(default=None),
) -> InstantlyWebhookResponse:
    settings = get_settings()
    raw_body = await request.body()
    if isinstance(body, InstantlyWebhookRequest):
        request_business_id = body.business_id
        request_environment = body.environment
        payload = body.payload
    else:
        if not business_id or not environment:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="business_id and environment query parameters are required for raw Instantly webhooks",
            )
        request_business_id = business_id
        request_environment = environment
        payload = body

    trusted = False
    if settings.provider_webhook_signatures_required or settings.instantly_webhook_secret:
        if not settings.instantly_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Instantly webhook secret is required",
            )
        if not verify_webhook_signature(settings.instantly_webhook_secret, x_instantly_signature, raw_body):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Instantly webhook signature",
            )
        trusted = True
        trust_reason = "signature_verified"
    elif x_instantly_signature:
        trust_reason = "signature_present_unverified"
    else:
        trust_reason = "signature_verification_not_configured"

    result = _build_write_path_service().handle_instantly_webhook(
        business_id=request_business_id,
        environment=request_environment,
        payload=payload,
        headers=dict(request.headers),
        trusted=trusted,
        trust_reason=str(trust_reason),
    )
    return InstantlyWebhookResponse(**result)


@router.post("/internal/nightly-source-pull", response_model=NightlySourcePullResponse)
def run_nightly_source_pull(request: NightlySourcePullRequest) -> NightlySourcePullResponse:
    try:
        return nightly_lead_machine_service.run_nightly_source_pull(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/internal/morning-brief", response_model=MorningBrief)
def build_morning_brief(request: MorningBriefRequest) -> MorningBrief:
    return nightly_lead_machine_service.create_morning_brief(request)


@router.post("/internal/followup-step-runner", response_model=FollowupStepRunnerResponse)
def run_followup_step_runner(request: FollowupStepRunnerRequest) -> FollowupStepRunnerResponse:
    suppressed = lead_suppression_service.is_suppressed(
        business_id=request.business_id,
        environment=request.environment,
        lead_id=request.lead_id,
        email=None,
        campaign_id=request.campaign_id,
    )
    if suppressed:
        return FollowupStepRunnerResponse(
            message_id=f"msg_{request.lead_id}_{request.day}_{request.channel}",
            channel=request.channel,
            status="stopped",
            suppressed=True,
        )

    result = inbound_sms_service.dispatch_lease_option_sequence_step(
        LeaseOptionSequenceStepRequest(
            lead_id=request.lead_id,
            business_id=request.business_id,
            environment=request.environment,
            day=request.day,
            channel=request.channel,
            template_id=request.template_id,
            manual_call_checkpoint=request.manual_call_checkpoint,
        )
    )
    return FollowupStepRunnerResponse(
        message_id=str(result["message_id"]),
        channel=str(result["channel"]),
        status=str(result["status"]),
        suppressed=False,
    )


@router.post("/internal/suppression-sync", response_model=SuppressionSyncResponse)
def sync_suppression(request: SuppressionSyncRequest) -> SuppressionSyncResponse:
    event = LeadEventRecord(
        business_id=request.business_id,
        environment=request.environment,
        lead_id=request.lead_id,
        campaign_id=request.campaign_id,
        provider_name=request.provider_name or "lead-machine",
        provider_event_id=request.provider_event_id,
        event_type=request.event_type,
        event_timestamp=request.event_timestamp or utc_now(),
        received_at=utc_now(),
        idempotency_key=request.idempotency_key or f"lead-machine-suppression:{request.event_type}:{request.lead_id}",
        payload={
            "lead_email": request.lead_email,
            "provider_name": request.provider_name,
            "provider_event_id": request.provider_event_id,
        },
        metadata={
            "source": "lead-machine",
        },
    )
    suppression = lead_suppression_service.apply_event(
        business_id=request.business_id,
        environment=request.environment,
        lead_id=request.lead_id,
        lead_email=request.lead_email,
        campaign_id=request.campaign_id,
        event=event,
    )
    lead_sequence_runner.handle_event(
        business_id=request.business_id,
        environment=request.environment,
        lead_id=request.lead_id,
        campaign_id=request.campaign_id,
        event=event,
    )
    return SuppressionSyncResponse(
        status="processed" if suppression is not None else "noop",
        suppression_id=suppression.id if suppression is not None else None,
        reason=suppression.reason if suppression is not None else None,
        active=suppression.active if suppression is not None else False,
        event_type=request.event_type,
    )


@router.post("/internal/task-reminder-or-overdue", response_model=TaskReminderOrOverdueResponse)
def remind_or_escalate_task(request: TaskReminderOrOverdueRequest) -> TaskReminderOrOverdueResponse:
    now = utc_now()
    overdue = request.status.lower() == "open" and request.due_at <= now
    if not overdue:
        return TaskReminderOrOverdueResponse(
            status="not_due",
            reminder_task_id=None,
            overdue=False,
            reminder_created=False,
        )

    reminder = TaskRecord(
        business_id=request.business_id,
        environment=request.environment,
        lead_id=request.lead_id,
        title=f"Reminder: {request.task_title}",
        status=TaskStatus.OPEN,
        task_type=TaskType.FOLLOW_UP,
        priority=TaskPriority(request.priority or ("urgent" if overdue else "normal")),
        due_at=now,
        assigned_to=request.assigned_to,
        idempotency_key=f"task-reminder:{request.task_id}",
        details={
            "source_task_id": request.task_id,
            "source_status": request.status,
            "source_due_at": request.due_at.isoformat(),
            "overdue": overdue,
        },
    )
    created = tasks_repository.create(reminder, dedupe_key=reminder.idempotency_key)
    return TaskReminderOrOverdueResponse(
        status="reminded" if not created.deduped else "deduped",
        reminder_task_id=created.id,
        overdue=True,
        reminder_created=True,
    )
