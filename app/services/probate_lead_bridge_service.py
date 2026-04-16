from __future__ import annotations

from typing import Any, Mapping

from app.db.leads import LeadsRepository
from app.models.leads import LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.probate_leads import ProbateLeadRecord


class ProbateLeadBridgeService:
    def __init__(self, leads_repository: LeadsRepository | None = None) -> None:
        self.leads_repository = leads_repository or LeadsRepository()

    def build_canonical_record(
        self,
        *,
        business_id: str,
        environment: str,
        probate_lead: ProbateLeadRecord | Mapping[str, Any],
    ) -> LeadRecord:
        record = probate_lead if isinstance(probate_lead, ProbateLeadRecord) else ProbateLeadRecord.model_validate(probate_lead)
        if not record.keep_now:
            raise ValueError("Probate lead must be keep-now before bridging")
        first_name, last_name = _split_name(record.owner_name or record.decedent_name)
        return LeadRecord(
            business_id=business_id,
            environment=environment,
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.READY,
            external_key=record.identity_key(),
            first_name=first_name,
            last_name=last_name,
            company_name=record.estate_name,
            mailing_address=record.mailing_address,
            property_address=record.property_address,
            probate_case_number=record.case_number,
            custom_variables={
                "court_number": record.court_number,
                "filing_type": record.filing_type,
                "filing_subtype": record.filing_subtype,
                "hcad_acct": record.hcad_acct,
                "hcad_match_status": record.hcad_match_status,
                "owner_name": record.owner_name,
                "contact_confidence": record.contact_confidence,
                "source": record.source,
            },
            raw_payload={"probate_lead": record.model_dump(mode="json")},
            score=record.lead_score,
            enrichment_status=str(record.hcad_match_status),
            verification_status=str(record.contact_confidence),
            status_summary=record.filing_type,
        )

    def upsert_keep_now_lead(
        self,
        *,
        business_id: str,
        environment: str,
        probate_lead: ProbateLeadRecord | Mapping[str, Any],
    ) -> LeadRecord:
        return self.leads_repository.upsert(
            self.build_canonical_record(
                business_id=business_id,
                environment=environment,
                probate_lead=probate_lead,
            )
        )


def _split_name(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    parts = [part for part in value.split() if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])
