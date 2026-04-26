from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.core.config import Settings, get_settings
from app.db.leads import LeadsRepository
from app.db.tasks import TasksRepository
from app.db.title_packets import TitlePacketsRepository
from app.models.leads import LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType
from app.models.title_packets import TitlePacketPriority, TitlePacketRecord, TitlePacketStatus

_SCHEMA = "ares.lead_import.v1"


@dataclass(frozen=True)
class TitlePacketImportResult:
    imported_count: int
    updated_count: int
    lead_ids: list[str]
    title_packet_ids: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)


class TitlePacketImportService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        repository: LeadsRepository | None = None,
        title_packets_repository: TitlePacketsRepository | None = None,
        tasks_repository: TasksRepository | None = None,
    ):
        self.settings = settings or get_settings()
        self.repository = repository or LeadsRepository(settings=self.settings)
        self.title_packets_repository = title_packets_repository or TitlePacketsRepository(settings=self.settings)
        self.tasks_repository = tasks_repository or TasksRepository(settings=self.settings)

    def import_payload(self, payload: Mapping[str, Any]) -> TitlePacketImportResult:
        schema = payload.get("schema")
        if schema != _SCHEMA:
            raise ValueError(f"expected schema {_SCHEMA}, got {schema!r}")

        records = payload.get("records")
        if not isinstance(records, list):
            raise ValueError("lead import payload requires a records list")

        source = str(payload.get("source") or "unknown")
        imported_count = 0
        updated_count = 0
        lead_ids: list[str] = []
        title_packet_ids: list[str] = []
        task_ids: list[str] = []

        for item in records:
            if not isinstance(item, Mapping):
                raise ValueError("each lead import record must be an object")

            record = self._build_record(item, import_source=source)
            existed = (
                self.repository.get_by_key(
                    business_id=record.business_id,
                    environment=record.environment,
                    dedupe_key=record.identity_key(),
                )
                is not None
            )
            saved = self.repository.upsert(record)
            if existed:
                updated_count += 1
            else:
                imported_count += 1
            if saved.id is not None:
                lead_ids.append(saved.id)

            packet = self.title_packets_repository.upsert(
                self._build_title_packet(item, lead=saved, import_source=source)
            )
            if packet.id is not None:
                title_packet_ids.append(packet.id)
            task = self._create_review_task(packet=packet, lead=saved)
            if task.id is not None:
                task_ids.append(task.id)

        return TitlePacketImportResult(
            imported_count=imported_count,
            updated_count=updated_count,
            lead_ids=lead_ids,
            title_packet_ids=title_packet_ids,
            task_ids=task_ids,
        )

    @staticmethod
    def _build_record(item: Mapping[str, Any], *, import_source: str) -> LeadRecord:
        raw_payload = dict(item.get("raw_payload") or {})
        raw_payload["import_source"] = import_source

        source = LeadSource(str(item.get("source") or LeadSource.PROBATE_INTAKE))
        if source == LeadSource.MANUAL:
            source = LeadSource.PROBATE_INTAKE

        return LeadRecord(
            business_id=str(item["business_id"]),
            environment=str(item["environment"]),
            source=source,
            lifecycle_status=LeadLifecycleStatus(str(item.get("lifecycle_status") or LeadLifecycleStatus.READY)),
            provider_name=item.get("provider_name"),
            provider_lead_id=item.get("provider_lead_id"),
            provider_workspace_id=item.get("provider_workspace_id"),
            external_key=item.get("external_key"),
            campaign_id=item.get("campaign_id"),
            list_id=item.get("list_id"),
            email=item.get("email"),
            phone=item.get("phone"),
            first_name=item.get("first_name"),
            last_name=item.get("last_name"),
            company_name=item.get("company_name"),
            company_domain=item.get("company_domain"),
            website=item.get("website"),
            job_title=item.get("job_title"),
            mailing_address=item.get("mailing_address"),
            property_address=item.get("property_address"),
            probate_case_number=item.get("probate_case_number"),
            personalization=dict(item.get("personalization") or {}),
            custom_variables=dict(item.get("custom_variables") or {}),
            raw_payload=raw_payload,
            score=item.get("score"),
            assigned_to=item.get("assigned_to"),
            verification_status=item.get("verification_status"),
            enrichment_status=item.get("enrichment_status"),
            upload_method=item.get("upload_method"),
        )

    @staticmethod
    def _build_title_packet(item: Mapping[str, Any], *, lead: LeadRecord, import_source: str) -> TitlePacketRecord:
        custom_variables = dict(item.get("custom_variables") or {})
        personalization = dict(item.get("personalization") or {})
        raw_payload = dict(item.get("raw_payload") or {})
        source_row = dict(raw_payload.get("source_row") or {})
        artifact_refs = [str(ref) for ref in raw_payload.get("packet_source_files") or []]
        facts = {
            "rank": custom_variables.get("rank"),
            "score": item.get("score"),
            "tax_due": custom_variables.get("tax_due"),
            "delinquent_years": custom_variables.get("delinquent_years"),
            "market_value": custom_variables.get("market_value"),
            "debt_to_value_pct": custom_variables.get("debt_to_value_pct"),
            "manual_pull_queue": custom_variables.get("manual_pull_queue"),
            "why_now": personalization.get("why_now"),
            "operator_posture": personalization.get("operator_posture"),
            "title_flags": personalization.get("title_flags"),
        }
        facts = {key: value for key, value in facts.items() if value is not None}
        priority = (
            TitlePacketPriority.HIGH
            if str(personalization.get("operator_lane") or "").startswith("A")
            else TitlePacketPriority.NORMAL
        )
        return TitlePacketRecord(
            business_id=lead.business_id,
            environment=lead.environment,
            external_key=str(lead.external_key or item["external_key"]),
            lead_id=lead.id,
            status=TitlePacketStatus.NEEDS_REVIEW,
            priority=priority,
            owner_name=lead.company_name or source_row.get("owner_tax"),
            estate_name=lead.company_name if "ESTATE" in str(lead.company_name or "").upper() else None,
            property_address=lead.property_address,
            mailing_address=lead.mailing_address,
            probate_case_number=lead.probate_case_number,
            hctax_account=custom_variables.get("hctax_account"),
            packet_source=import_source,
            operator_lane=personalization.get("operator_lane"),
            assigned_to=lead.assigned_to,
            artifact_refs=artifact_refs,
            facts=facts,
            raw_payload={
                "source_row": source_row,
                "custom_variables": custom_variables,
                "personalization": personalization,
            },
        )

    def _create_review_task(self, *, packet: TitlePacketRecord, lead: LeadRecord) -> TaskRecord:
        title_subject = packet.property_address or packet.owner_name or packet.external_key
        return self.tasks_repository.create(
            TaskRecord(
                business_id=packet.business_id,
                environment=packet.environment,
                lead_id=lead.id,
                title=f"Review title packet: {title_subject}",
                status=TaskStatus.OPEN,
                task_type=TaskType.MANUAL_REVIEW,
                priority=TaskPriority.HIGH
                if packet.priority in {TitlePacketPriority.HIGH, TitlePacketPriority.URGENT}
                else TaskPriority.NORMAL,
                assigned_to=packet.assigned_to,
                idempotency_key=f"title-packet-review:{packet.identity_key()}",
                details={
                    "source": "title_packet_import",
                    "title_packet_id": packet.id,
                    "external_key": packet.external_key,
                    "property_address": packet.property_address,
                    "probate_case_number": packet.probate_case_number,
                    "hctax_account": packet.hctax_account,
                    "operator_lane": packet.operator_lane,
                    "manual_pull_queue": packet.facts.get("manual_pull_queue"),
                    "packet_status": packet.status,
                },
            ),
            dedupe_key=f"title-packet-review:{packet.identity_key()}",
        )
