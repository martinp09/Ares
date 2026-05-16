from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.db.deals import DealsRepository
from app.db.leads import LeadsRepository
from app.models.deals import (
    Deal,
    DealAuditEvent,
    DealAuditEventType,
    DealDetail,
    DealDocumentRequirement,
    DealParty,
    DealPartyRole,
    DealRiskFlag,
    DealRiskSeverity,
    DealSourceLane,
    DealStage,
    DealStageEvent,
    DealStrategyLane,
    DealTask,
    DealTaskType,
    default_provider_gate_snapshot,
)
from app.models.leads import LeadRecord
from app.models.commands import utc_now


class DealPromotionService:
    def __init__(
        self,
        *,
        deals_repository: DealsRepository | None = None,
        leads_repository: LeadsRepository | None = None,
    ) -> None:
        self.deals_repository = deals_repository or DealsRepository()
        self.leads_repository = leads_repository or LeadsRepository()

    def promote_lead_to_deal(
        self,
        lead_id: str,
        *,
        business_id: str,
        environment: str,
        source_lane: DealSourceLane,
        strategy_lane: DealStrategyLane,
        actor_id: str | None = None,
        actor_type: str | None = None,
        promotion_reason: str | None = None,
        operator_notes: str | None = None,
        no_send: bool = True,
    ) -> DealDetail:
        if not no_send:
            raise ValueError("Back Office Spine v0 is no-send only; deal promotion cannot clear no_send")

        lead = self.leads_repository.get(lead_id)
        if lead is None or lead.business_id != business_id or lead.environment != environment:
            raise KeyError(f"lead {lead_id} not found")

        dedupe_key = f"lead:{source_lane.value}:{lead_id}"
        existing = self.deals_repository.get_deal_by_identity(
            business_id=business_id,
            environment=environment,
            dedupe_key=dedupe_key,
        )
        deal = self.deals_repository.upsert_deal(
            self._deal_from_lead(
                lead,
                source_lane=source_lane,
                strategy_lane=strategy_lane,
                no_send=no_send,
                promotion_reason=promotion_reason,
                operator_notes=operator_notes,
            ),
            dedupe_key=dedupe_key,
        )
        assert deal.id is not None

        self._ensure_parties(deal, lead)
        self._ensure_template_children(deal)
        self._ensure_initial_events(
            deal,
            existing=existing,
            actor_id=actor_id,
            actor_type=actor_type,
            promotion_reason=promotion_reason,
        )
        detail = self.deals_repository.get_detail(deal.id)
        if detail is None:  # pragma: no cover - defensive repository invariant
            raise RuntimeError(f"deal {deal.id} was not persisted")
        return detail

    def _deal_from_lead(
        self,
        lead: LeadRecord,
        *,
        source_lane: DealSourceLane,
        strategy_lane: DealStrategyLane,
        no_send: bool,
        promotion_reason: str | None,
        operator_notes: str | None,
    ) -> Deal:
        raw_payload = lead.raw_payload if isinstance(lead.raw_payload, dict) else {}
        facts = {
            "lead_source": lead.source.value,
            "email": lead.email,
            "phone": lead.phone,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "score": lead.score,
        }
        facts.update({key: value for key, value in lead.custom_variables.items() if value not in (None, "")})
        return Deal(
            business_id=lead.business_id,
            environment=lead.environment,
            source_lane=source_lane,
            strategy_lane=strategy_lane,
            stage=DealStage.QUALIFIED,
            source_record_id=lead.id,
            source_lead_id=lead.id,
            probate_case_number=lead.probate_case_number,
            property_address=lead.property_address,
            mailing_address=lead.mailing_address,
            county=raw_payload.get("county"),
            no_send=no_send,
            provider_sends_enabled=False,
            provider_gate_snapshot=default_provider_gate_snapshot(),
            source_evidence=[
                {
                    "type": "lead_record",
                    "lead_id": lead.id,
                    "external_key": lead.external_key,
                    "probate_case_number": lead.probate_case_number,
                    "case_detail_url": raw_payload.get("case_detail_url"),
                }
            ],
            facts=facts,
            metadata={
                "promotion_reason": promotion_reason,
                "operator_notes": operator_notes,
                "source_raw_payload_keys": sorted(raw_payload.keys()),
            },
            next_action=self._initial_next_action(strategy_lane),
        )

    def _ensure_parties(self, deal: Deal, lead: LeadRecord) -> None:
        assert deal.id is not None
        raw_payload = lead.raw_payload if isinstance(lead.raw_payload, dict) else {}
        contact_candidates = raw_payload.get("contact_candidates")
        seeded = False
        if isinstance(contact_candidates, list):
            for candidate in contact_candidates:
                if not isinstance(candidate, dict) or not candidate.get("name"):
                    continue
                self.deals_repository.add_party(
                    DealParty(
                        business_id=deal.business_id,
                        environment=deal.environment,
                        deal_id=deal.id,
                        name=str(candidate["name"]),
                        role=DealPartyRole.CONTACT_CANDIDATE,
                        role_confidence="medium",
                        authority_status="contact_candidate_only",
                        source_evidence=[dict(candidate)],
                    )
                )
                seeded = True
        fallback_name = " ".join(part for part in [lead.first_name, lead.last_name] if part).strip()
        if not seeded and fallback_name:
            self.deals_repository.add_party(
                DealParty(
                    business_id=deal.business_id,
                    environment=deal.environment,
                    deal_id=deal.id,
                    name=fallback_name,
                    role=DealPartyRole.CONTACT_CANDIDATE,
                    role_confidence="low",
                    authority_status="contact_candidate_only",
                    phone=lead.phone,
                    email=lead.email,
                    mailing_address=lead.mailing_address,
                    source_evidence=[{"type": "lead_record", "lead_id": lead.id}],
                )
            )

    def _ensure_template_children(self, deal: Deal) -> None:
        assert deal.id is not None
        for task in self._default_tasks_for(deal):
            self.deals_repository.upsert_task(task)
        for requirement in self._default_document_requirements_for(deal):
            self.deals_repository.upsert_document_requirement(requirement)
        for risk in self._default_risk_flags_for(deal):
            self.deals_repository.upsert_risk_flag(risk)

    def _default_tasks_for(self, deal: Deal) -> list[DealTask]:
        assert deal.id is not None
        due = utc_now() + timedelta(days=1)
        base = {
            "business_id": deal.business_id,
            "environment": deal.environment,
            "deal_id": deal.id,
            "due_at": due,
            "created_from": "lane_template",
        }
        if deal.strategy_lane == DealStrategyLane.CURATIVE_TITLE:
            return [
                DealTask(**base, task_type=DealTaskType.VERIFY_AUTHORITY, title="Verify seller authority"),
                DealTask(**base, task_type=DealTaskType.BUILD_HEIR_MAP, title="Build heir map"),
                DealTask(**base, task_type=DealTaskType.PULL_DEED_CHAIN, title="Pull deed chain"),
                DealTask(**base, task_type=DealTaskType.TAX_PAYOFF_CHECK, title="Run tax payoff check"),
                DealTask(**base, task_type=DealTaskType.TITLE_COMPANY_CONSULT, title="Prepare title company consult"),
            ]
        if deal.strategy_lane == DealStrategyLane.LEASE_OPTION:
            return [
                DealTask(**base, task_type=DealTaskType.CONFIRM_MORTGAGE_BALANCE, title="Confirm mortgage balance"),
                DealTask(**base, task_type=DealTaskType.CONFIRM_PITI, title="Confirm PITI"),
                DealTask(**base, task_type=DealTaskType.CONFIRM_OCCUPANCY, title="Confirm occupancy"),
                DealTask(**base, task_type=DealTaskType.OFFER_REVIEW, title="Draft lease-option offer workup"),
            ]
        return [
            DealTask(**base, task_type=DealTaskType.MANUAL_CALL, title="Call seller/contact candidate"),
            DealTask(**base, task_type=DealTaskType.RUN_COMPS, title="Run comps"),
            DealTask(**base, task_type=DealTaskType.OFFER_REVIEW, title="Draft offer workup"),
        ]

    def _default_document_requirements_for(self, deal: Deal) -> list[DealDocumentRequirement]:
        assert deal.id is not None
        base = {"business_id": deal.business_id, "environment": deal.environment, "deal_id": deal.id}
        if deal.strategy_lane == DealStrategyLane.CURATIVE_TITLE:
            return [
                DealDocumentRequirement(
                    **base,
                    document_type="letters_testamentary_or_administration",
                    required_stage=DealStage.CONTACT_READY,
                    approval_required=True,
                ),
                DealDocumentRequirement(**base, document_type="affidavit_of_heirship", required_stage=DealStage.UNDER_CONTRACT),
                DealDocumentRequirement(**base, document_type="deed_chain", required_stage=DealStage.UNDER_CONTRACT),
                DealDocumentRequirement(
                    **base,
                    document_type="executed_purchase_contract",
                    required_stage=DealStage.UNDER_CONTRACT,
                    approval_required=True,
                ),
            ]
        if deal.strategy_lane == DealStrategyLane.LEASE_OPTION:
            return [
                DealDocumentRequirement(**base, document_type="mortgage_statement", required_stage=DealStage.OFFER_NEEDED),
                DealDocumentRequirement(**base, document_type="lease_option_terms", required_stage=DealStage.OFFER_DRAFTED),
                DealDocumentRequirement(
                    **base,
                    document_type="texas_lease_option_compliance_checklist",
                    required_stage=DealStage.OFFER_APPROVED,
                    approval_required=True,
                ),
            ]
        return [
            DealDocumentRequirement(**base, document_type="seller_offer_summary", required_stage=DealStage.OFFER_DRAFTED),
            DealDocumentRequirement(**base, document_type="executed_purchase_contract", required_stage=DealStage.UNDER_CONTRACT),
        ]

    def _default_risk_flags_for(self, deal: Deal) -> list[DealRiskFlag]:
        assert deal.id is not None
        flags = [
            DealRiskFlag(
                business_id=deal.business_id,
                environment=deal.environment,
                deal_id=deal.id,
                code="provider_sends_blocked",
                label="Provider sends remain blocked until explicit approval",
                severity=DealRiskSeverity.MEDIUM,
                source="back_office_spine_v0",
            )
        ]
        if deal.strategy_lane == DealStrategyLane.CURATIVE_TITLE:
            flags.append(
                DealRiskFlag(
                    business_id=deal.business_id,
                    environment=deal.environment,
                    deal_id=deal.id,
                    code="authority_unverified",
                    label="Seller authority is not verified",
                    severity=DealRiskSeverity.HIGH,
                    source="back_office_spine_v0",
                )
            )
        return flags

    def _ensure_initial_events(
        self,
        deal: Deal,
        *,
        existing: Deal | None,
        actor_id: str | None,
        actor_type: str | None,
        promotion_reason: str | None,
    ) -> None:
        assert deal.id is not None
        if existing is not None:
            return
        self.deals_repository.add_stage_event(
            DealStageEvent(
                business_id=deal.business_id,
                environment=deal.environment,
                deal_id=deal.id,
                from_stage=None,
                to_stage=deal.stage,
                actor_id=actor_id,
                actor_type=actor_type,
                reason=promotion_reason,
                metadata={"source": "deal_promotion"},
            ),
            dedupe_key=f"initial:{deal.id}",
        )
        self.deals_repository.add_audit_event(
            DealAuditEvent(
                business_id=deal.business_id,
                environment=deal.environment,
                deal_id=deal.id,
                event_type=DealAuditEventType.DEAL_PROMOTED,
                actor_id=actor_id,
                actor_type=actor_type,
                after_state=deal.model_dump(mode="json"),
                provider_gate_snapshot=deal.provider_gate_snapshot,
                notes=promotion_reason,
                metadata={"no_send": deal.no_send, "provider_sends_enabled": deal.provider_sends_enabled},
            ),
            dedupe_key=f"promoted:{deal.id}",
        )

    @staticmethod
    def _initial_next_action(strategy_lane: DealStrategyLane) -> str:
        if strategy_lane == DealStrategyLane.CURATIVE_TITLE:
            return "Verify authority and property/title evidence before outreach"
        if strategy_lane == DealStrategyLane.LEASE_OPTION:
            return "Confirm mortgage/PITI facts before offer workup"
        return "Review seller motivation and run comps"


deal_promotion_service = DealPromotionService()
