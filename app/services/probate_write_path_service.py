from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from app.core.config import Settings, get_settings
from app.db.probate_leads import ProbateLeadsRepository
from app.models.leads import LeadRecord
from app.models.probate_leads import ProbateLeadRecord
from app.providers.instantly import InstantlyClient
from app.services.harris_probate_intake_service import HarrisProbateIntakeService
from app.services.lead_outbound_service import LeadOutboundService, OutboundEnrollmentRequest, OutboundEnrollmentResult
from app.services.lead_webhook_service import LeadWebhookService
from app.services.probate_hcad_match_service import ProbateHCADMatchService
from app.services.probate_lead_bridge_service import ProbateLeadBridgeService
from app.services.probate_lead_score_service import ProbateLeadScoreService


class ProbateWritePathService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        intake_service: HarrisProbateIntakeService | None = None,
        hcad_match_service: ProbateHCADMatchService | None = None,
        score_service: ProbateLeadScoreService | None = None,
        probate_leads_repository: ProbateLeadsRepository | None = None,
        lead_bridge_service: ProbateLeadBridgeService | None = None,
        outbound_service: LeadOutboundService | None = None,
        webhook_service: LeadWebhookService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.intake_service = intake_service or HarrisProbateIntakeService()
        self.hcad_match_service = hcad_match_service or ProbateHCADMatchService()
        self.score_service = score_service or ProbateLeadScoreService()
        self.probate_leads_repository = probate_leads_repository or ProbateLeadsRepository()
        self.lead_bridge_service = lead_bridge_service or ProbateLeadBridgeService()
        self._outbound_service = outbound_service
        self._webhook_service = webhook_service or LeadWebhookService()

    def intake_probate_cases(
        self,
        *,
        business_id: str,
        environment: str,
        payloads: Iterable[Mapping[str, Any]],
        hcad_candidates_by_case: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
        keep_only: bool = True,
    ) -> dict[str, Any]:
        payload_rows = list(payloads)
        lead_records: list[LeadRecord] = []
        lead_ids: list[str] = []
        records: list[dict[str, Any]] = []
        kept_count = 0
        for payload in payload_rows:
            normalized = self.intake_service.normalize_case(payload)
            enriched = self._enrich_probate_record(
                normalized,
                payload=payload,
                hcad_candidates_by_case=hcad_candidates_by_case,
            )
            persisted_probate_lead = self.probate_leads_repository.upsert(
                business_id=business_id,
                environment=environment,
                record=enriched,
            )
            if keep_only and not persisted_probate_lead.keep_now:
                continue
            kept_count += 1
            bridged_lead_id: str | None = None
            if persisted_probate_lead.keep_now:
                canonical = self.lead_bridge_service.upsert_keep_now_lead(
                    business_id=business_id,
                    environment=environment,
                    probate_lead=persisted_probate_lead,
                )
                lead_records.append(canonical)
                if canonical.id is not None:
                    lead_ids.append(canonical.id)
                    bridged_lead_id = canonical.id
            records.append(
                {
                    "case_number": persisted_probate_lead.case_number,
                    "keep_now": persisted_probate_lead.keep_now,
                    "lead_score": persisted_probate_lead.lead_score,
                    "hcad_match_status": str(persisted_probate_lead.hcad_match_status),
                    "contact_confidence": str(persisted_probate_lead.contact_confidence),
                    "bridged_lead_id": bridged_lead_id,
                }
            )
        return {
            "received_count": len(payload_rows),
            "kept_count": kept_count,
            "lead_ids": lead_ids,
            "leads": lead_records,
            "processed_count": len(records),
            "keep_now_count": kept_count,
            "bridged_count": sum(1 for record in records if record["bridged_lead_id"] is not None),
            "records": records,
        }

    def enqueue_probate_leads(
        self,
        *,
        business_id: str,
        environment: str,
        lead_ids: list[str],
        campaign_id: str | None = None,
        list_id: str | None = None,
        skip_if_in_workspace: bool = True,
        skip_if_in_campaign: bool = True,
        skip_if_in_list: bool = True,
        blocklist_id: str | None = None,
        assigned_to: str | None = None,
        verify_leads_on_import: bool = False,
        chunk_size: int | None = None,
        wait_seconds: float | None = None,
    ) -> OutboundEnrollmentResult:
        service = self._get_outbound_service()
        return service.enqueue_leads(
            OutboundEnrollmentRequest(
                business_id=business_id,
                environment=environment,
                lead_ids=lead_ids,
                campaign_id=campaign_id,
                list_id=list_id,
                skip_if_in_workspace=skip_if_in_workspace,
                skip_if_in_campaign=skip_if_in_campaign,
                skip_if_in_list=skip_if_in_list,
                blocklist_id=blocklist_id,
                assigned_to=assigned_to,
                verify_leads_on_import=verify_leads_on_import,
                chunk_size=chunk_size,
                wait_seconds=wait_seconds,
            )
        )

    def handle_instantly_webhook(
        self,
        *,
        business_id: str,
        environment: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, Any] | None = None,
        trusted: bool = False,
        trust_reason: str | None = None,
    ) -> dict[str, Any]:
        return self._webhook_service.handle_instantly_webhook(
            business_id=business_id,
            environment=environment,
            payload=payload,
            headers=headers,
            trusted=trusted,
            trust_reason=trust_reason,
        )

    def _enrich_probate_record(
        self,
        record: ProbateLeadRecord,
        *,
        payload: Mapping[str, Any],
        hcad_candidates_by_case: Mapping[str, Iterable[Mapping[str, Any]]] | None,
    ) -> ProbateLeadRecord:
        candidates = list((hcad_candidates_by_case or {}).get(record.case_number, []))
        matched = self.hcad_match_service.match_lead(record, candidates) if candidates else record
        overlay_updates = self._overlay_updates(payload)
        if overlay_updates:
            matched = ProbateLeadRecord.model_validate(
                {
                    **matched.model_dump(mode="python"),
                    **overlay_updates,
                }
            )
        return self.score_service.score_lead(matched)

    @staticmethod
    def _overlay_updates(payload: Mapping[str, Any]) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        allowed_fields = set(ProbateLeadRecord.model_fields)
        for field_name in (
            "keep_now",
            "hcad_match_status",
            "hcad_acct",
            "owner_name",
            "mailing_address",
            "property_address",
            "contact_confidence",
            "matched_candidate_count",
            "outreach_status",
            "source",
            "tax_delinquent",
            "estate_of",
            "pain_stack",
        ):
            if field_name in payload and field_name in allowed_fields and payload[field_name] is not None:
                updates[field_name] = payload[field_name]
        return updates

    def _get_outbound_service(self) -> LeadOutboundService:
        if self._outbound_service is not None:
            return self._outbound_service
        api_key = self.settings.instantly_api_key
        if not api_key:
            raise RuntimeError("INSTANTLY_API_KEY is required to enqueue outbound leads")
        self._outbound_service = LeadOutboundService(
            instantly_client=InstantlyClient(
                api_key=api_key,
                base_url=self.settings.instantly_base_url,
                batch_size=self.settings.instantly_batch_size,
                batch_wait_seconds=self.settings.instantly_batch_wait_seconds,
            )
        )
        return self._outbound_service


probate_write_path_service = ProbateWritePathService()
