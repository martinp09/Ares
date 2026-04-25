from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.db.leads import LeadsRepository
from app.models.leads import LeadLifecycleStatus, LeadRecord, LeadSource

_SCHEMA = "ares.lead_import.v1"


@dataclass(frozen=True)
class TitlePacketImportResult:
    imported_count: int
    updated_count: int
    lead_ids: list[str]


class TitlePacketImportService:
    """Import operator-built title packet leads into Ares canonical lead storage."""

    def __init__(self, repository: LeadsRepository | None = None):
        self.repository = repository or LeadsRepository()

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

        return TitlePacketImportResult(
            imported_count=imported_count,
            updated_count=updated_count,
            lead_ids=lead_ids,
        )

    @staticmethod
    def _build_record(item: Mapping[str, Any], *, import_source: str) -> LeadRecord:
        raw_payload = dict(item.get("raw_payload") or {})
        raw_payload["import_source"] = import_source

        return LeadRecord(
            business_id=str(item["business_id"]),
            environment=str(item["environment"]),
            source=LeadSource(str(item.get("source") or LeadSource.MANUAL)),
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
