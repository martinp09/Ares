from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.models.commands import utc_now
from app.models.lead_events import LeadEventRecord
from app.models.leads import LeadLifecycleStatus, LeadRecord, LeadSource


@dataclass(slots=True)
class LeadIntakeRequest:
    business_id: str
    environment: str
    source: str = "manual"
    source_record_id: str | None = None
    campaign_key: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    property_address: str | None = None
    county: str | None = None
    status: str = "new"
    pipeline_stage: str | None = None
    priority: str | None = None
    dedupe_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LeadIntakeResult:
    lead: LeadRecord
    intake_event: LeadEventRecord
    status: str
    queued: bool = False
    skipped: bool = False
    failed_side_effects: list[str] = field(default_factory=list)


class LeadIntakeService:
    def __init__(
        self,
        *,
        leads_repository: LeadsRepository | None = None,
        lead_events_repository: LeadEventsRepository | None = None,
    ) -> None:
        self.leads_repository = leads_repository or LeadsRepository()
        self.lead_events_repository = lead_events_repository or LeadEventsRepository()

    def intake_lead(self, request: LeadIntakeRequest) -> LeadIntakeResult:
        self._lead_source(request.source)
        dedupe_key = self._dedupe_key(request)
        existing = self.leads_repository.get_by_key(
            business_id=request.business_id,
            environment=request.environment,
            dedupe_key=dedupe_key,
        )
        lead = self.leads_repository.upsert(self._lead_record(request), dedupe_key=dedupe_key)
        event = self.lead_events_repository.append(
            LeadEventRecord(
                business_id=request.business_id,
                environment=request.environment,
                lead_id=lead.id or "",
                campaign_id=lead.campaign_id,
                provider_name=None,
                event_type="lead.intake.created",
                event_timestamp=utc_now(),
                idempotency_key=f"lead-intake:{request.business_id}:{request.environment}:{dedupe_key}",
                payload={
                    "source": request.source,
                    "source_record_id": request.source_record_id,
                    "campaign_key": request.campaign_key,
                    "status": request.status,
                    "pipeline_stage": request.pipeline_stage,
                    "priority": request.priority,
                },
                metadata=dict(request.metadata),
            )
        )
        return LeadIntakeResult(
            lead=lead,
            intake_event=event,
            status="deduped" if existing is not None or event.deduped else "created",
        )

    def _lead_record(self, request: LeadIntakeRequest) -> LeadRecord:
        metadata = dict(request.metadata)
        for key, value in {
            "source": request.source,
            "source_record_id": request.source_record_id,
            "campaign_key": request.campaign_key,
            "county": request.county,
            "status": request.status,
            "pipeline_stage": request.pipeline_stage,
            "priority": request.priority,
            "dedupe_key": request.dedupe_key,
        }.items():
            if value is not None:
                metadata.setdefault(key, value)
        return LeadRecord(
            business_id=request.business_id,
            environment=request.environment,
            source=self._lead_source(request.source),
            lifecycle_status=self._lifecycle_status(request.status),
            external_key=self._external_key(request),
            email=request.email,
            phone=request.phone,
            first_name=request.first_name,
            last_name=request.last_name,
            property_address=request.property_address,
            raw_payload=metadata,
        )

    @staticmethod
    def _lead_source(source: str) -> LeadSource:
        try:
            return LeadSource(source)
        except ValueError:
            allowed = ", ".join(sorted(item.value for item in LeadSource))
            raise ValueError(f"unsupported lead source {source!r}; expected one of: {allowed}")

    @staticmethod
    def _lifecycle_status(status: str) -> LeadLifecycleStatus:
        try:
            return LeadLifecycleStatus(status)
        except ValueError:
            return LeadLifecycleStatus.NEW

    @staticmethod
    def _dedupe_key(request: LeadIntakeRequest) -> str:
        if request.dedupe_key:
            return request.dedupe_key
        if request.source_record_id:
            return f"external:{LeadIntakeService._external_key(request).casefold()}"
        if request.email:
            return f"email:{request.email.strip().casefold()}"
        if request.phone:
            return f"phone:{''.join(request.phone.split())}"
        raise ValueError("dedupe_key, source_record_id, email, or phone is required")

    @staticmethod
    def _external_key(request: LeadIntakeRequest) -> str | None:
        if not request.source_record_id:
            return None
        source = request.source.strip().casefold()
        source_record_id = request.source_record_id.strip()
        return f"{source}:{source_record_id}"


lead_intake_service = LeadIntakeService()
