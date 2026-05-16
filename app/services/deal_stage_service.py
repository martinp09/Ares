from __future__ import annotations

from app.db.deals import DealsRepository
from app.models.deals import (
    DealAuditEvent,
    DealAuditEventType,
    DealDetail,
    DealDocumentRequirementStatus,
    DealRiskSeverity,
    DealStage,
    DealStageEvent,
)

_STAGE_ORDER = {
    DealStage.QUALIFIED: 0,
    DealStage.CONTACT_READY: 1,
    DealStage.CONTACTED: 2,
    DealStage.REPLIED: 3,
    DealStage.APPOINTMENT_SET: 4,
    DealStage.APPOINTMENT_COMPLETED: 5,
    DealStage.OFFER_NEEDED: 6,
    DealStage.OFFER_DRAFTED: 7,
    DealStage.OFFER_APPROVED: 8,
    DealStage.OFFER_SENT: 9,
    DealStage.VERBAL_YES: 10,
    DealStage.UNDER_CONTRACT: 11,
    DealStage.TITLE_OPENED: 12,
    DealStage.DISPO_READY: 13,
    DealStage.BUYER_SELECTED: 14,
    DealStage.CLEAR_TO_CLOSE: 15,
    DealStage.CLOSING_SCHEDULED: 16,
    DealStage.FUNDED_CLOSED: 17,
    DealStage.CLOSED: 18,
    DealStage.DEAD: 99,
    DealStage.NURTURE: 100,
}
_TERMINAL = {DealStage.CLOSED, DealStage.DEAD}
_RECEIVED_DOCUMENT_STATUSES = {
    DealDocumentRequirementStatus.RECEIVED,
    DealDocumentRequirementStatus.REVIEWED,
    DealDocumentRequirementStatus.APPROVED,
}


class DealStageService:
    def __init__(self, *, deals_repository: DealsRepository | None = None) -> None:
        self.deals_repository = deals_repository or DealsRepository()

    def transition_stage(
        self,
        deal_id: str,
        target_stage: DealStage,
        *,
        actor_id: str | None = None,
        actor_type: str | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
        manual_override: bool = False,
    ) -> DealDetail:
        deal = self.deals_repository.get_deal(deal_id)
        if deal is None:
            raise KeyError(deal_id)
        metadata_payload = dict(metadata or {})
        self._validate_transition(deal_id, deal.stage, target_stage, metadata_payload, manual_override=manual_override)
        previous = deal
        updated = self.deals_repository.upsert_deal(deal.model_copy(update={"stage": target_stage}))
        if previous.stage != target_stage:
            self.deals_repository.add_stage_event(
                DealStageEvent(
                    business_id=deal.business_id,
                    environment=deal.environment,
                    deal_id=deal_id,
                    from_stage=previous.stage,
                    to_stage=target_stage,
                    actor_id=actor_id,
                    actor_type=actor_type,
                    reason=reason,
                    metadata={**metadata_payload, "manual_override": manual_override},
                )
            )
            self.deals_repository.add_audit_event(
                DealAuditEvent(
                    business_id=deal.business_id,
                    environment=deal.environment,
                    deal_id=deal_id,
                    event_type=DealAuditEventType.STAGE_CHANGED,
                    actor_id=actor_id,
                    actor_type=actor_type,
                    before_state=previous.model_dump(mode="json"),
                    after_state=updated.model_dump(mode="json"),
                    provider_gate_snapshot=updated.provider_gate_snapshot,
                    notes=reason,
                    metadata={**metadata_payload, "manual_override": manual_override},
                )
            )
        detail = self.deals_repository.get_detail(deal_id)
        if detail is None:  # pragma: no cover
            raise RuntimeError(f"deal {deal_id} was not persisted")
        return detail

    def _validate_transition(
        self,
        deal_id: str,
        current_stage: DealStage,
        target_stage: DealStage,
        metadata: dict,
        *,
        manual_override: bool,
    ) -> None:
        if current_stage in _TERMINAL and target_stage != current_stage:
            raise ValueError(f"cannot move terminal deal from {current_stage.value} to {target_stage.value}")
        if _STAGE_ORDER[target_stage] < _STAGE_ORDER[current_stage]:
            raise ValueError(f"cannot move deal backward from {current_stage.value} to {target_stage.value}")
        if self._has_missing_document_blocker(deal_id, target_stage, metadata) and not manual_override:
            raise ValueError(f"{target_stage.value} is blocked by missing required document evidence")
        if target_stage == DealStage.UNDER_CONTRACT:
            has_contract_evidence = bool(metadata.get("executed_contract_evidence")) or self._has_received_document(
                deal_id,
                "executed_purchase_contract",
            )
            if not has_contract_evidence and not manual_override:
                raise ValueError("under_contract requires executed contract evidence or manual override")
            if self._has_unresolved_critical_risk(deal_id) and not manual_override:
                raise ValueError("under_contract is blocked by unresolved critical risk")
        if target_stage in {DealStage.DISPO_READY, DealStage.BUYER_SELECTED}:
            if not (manual_override or metadata.get("contract_verified") or current_stage == DealStage.UNDER_CONTRACT):
                raise ValueError("dispo requires contract must be verified or manual override")

    def _has_received_document(self, deal_id: str, document_type: str) -> bool:
        return any(
            requirement.document_type == document_type
            and requirement.status in _RECEIVED_DOCUMENT_STATUSES
            for requirement in self.deals_repository.list_document_requirements(deal_id)
        )

    def _has_missing_document_blocker(self, deal_id: str, target_stage: DealStage, metadata: dict) -> bool:
        target_order = _STAGE_ORDER[target_stage]
        for requirement in self.deals_repository.list_document_requirements(deal_id):
            if _STAGE_ORDER[requirement.required_stage] > target_order:
                continue
            if requirement.status in _RECEIVED_DOCUMENT_STATUSES:
                continue
            if requirement.document_type == "executed_purchase_contract":
                continue
            return True
        return False

    def _has_unresolved_critical_risk(self, deal_id: str) -> bool:
        return any(
            flag.active and flag.severity == DealRiskSeverity.CRITICAL
            for flag in self.deals_repository.list_risk_flags(deal_id)
        )


deal_stage_service = DealStageService()
