from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.deals import DealsRepository
from app.models.deals import (
    Deal,
    DealAuditEventType,
    DealDocumentRequirement,
    DealRiskFlag,
    DealRiskSeverity,
    DealSourceLane,
    DealStage,
    DealStrategyLane,
)
from app.services.deal_stage_service import DealStageService


def _service() -> tuple[DealStageService, DealsRepository, Deal]:
    store = InMemoryControlPlaneStore()
    repo = DealsRepository(client=InMemoryControlPlaneClient(store))
    deal = repo.upsert_deal(
        Deal(
            business_id="limitless",
            environment="dev",
            source_lane=DealSourceLane.HARRIS_PROBATE,
            strategy_lane=DealStrategyLane.CURATIVE_TITLE,
            source_record_id="lead_341",
        )
    )
    return DealStageService(deals_repository=repo), repo, deal


def test_stage_transition_allows_forward_move_and_records_events() -> None:
    service, repo, deal = _service()
    assert deal.id is not None

    detail = service.transition_stage(
        deal.id,
        DealStage.CONTACT_READY,
        actor_id="martin",
        actor_type="user",
        reason="suppression clear and contact candidate exists",
    )

    assert detail.deal.stage == DealStage.CONTACT_READY
    assert detail.stage_events[-1].from_stage == DealStage.QUALIFIED
    assert detail.stage_events[-1].to_stage == DealStage.CONTACT_READY
    assert detail.audit_events[-1].event_type == DealAuditEventType.STAGE_CHANGED
    assert repo.get_deal(deal.id).stage == DealStage.CONTACT_READY


def test_missing_required_document_blocks_required_stage_without_override() -> None:
    service, repo, deal = _service()
    assert deal.id is not None
    repo.upsert_document_requirement(
        DealDocumentRequirement(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            document_type="letters_testamentary_or_administration",
            required_stage=DealStage.CONTACT_READY,
        )
    )

    try:
        service.transition_stage(deal.id, DealStage.CONTACT_READY, reason="operator wants outreach ready")
    except ValueError as exc:
        assert "missing required document evidence" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("contact_ready transition was allowed with missing required document")

    detail = service.transition_stage(
        deal.id,
        DealStage.CONTACT_READY,
        manual_override=True,
        reason="operator verified authority document offline",
    )
    assert detail.deal.stage == DealStage.CONTACT_READY


def test_under_contract_requires_executed_contract_evidence_or_manual_override() -> None:
    service, _repo, deal = _service()
    assert deal.id is not None

    try:
        service.transition_stage(deal.id, DealStage.UNDER_CONTRACT, reason="seller said yes")
    except ValueError as exc:
        assert "executed contract evidence" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("under_contract transition was allowed without executed contract evidence")

    approved = service.transition_stage(
        deal.id,
        DealStage.UNDER_CONTRACT,
        manual_override=True,
        reason="operator verified signed agreement offline",
        metadata={"executed_contract_evidence": "uploaded:contract.pdf"},
    )
    assert approved.deal.stage == DealStage.UNDER_CONTRACT
    assert approved.audit_events[-1].metadata["manual_override"] is True


def test_dispo_requires_contract_verified_or_manual_override() -> None:
    service, _repo, deal = _service()
    assert deal.id is not None

    try:
        service.transition_stage(deal.id, DealStage.DISPO_READY, reason="looks marketable")
    except ValueError as exc:
        assert "contract must be verified" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("dispo transition was allowed without contract verification")


def test_critical_risk_blocks_high_risk_stage_without_override() -> None:
    service, repo, deal = _service()
    assert deal.id is not None
    repo.upsert_risk_flag(
        DealRiskFlag(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            code="authority_conflict",
            label="Conflicting seller authority",
            severity=DealRiskSeverity.CRITICAL,
        )
    )
    repo.upsert_document_requirement(
        DealDocumentRequirement(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            document_type="executed_purchase_contract",
            required_stage=DealStage.UNDER_CONTRACT,
            status="received",
        )
    )

    try:
        service.transition_stage(
            deal.id,
            DealStage.UNDER_CONTRACT,
            reason="contract uploaded but risk unresolved",
            metadata={"executed_contract_evidence": "uploaded:contract.pdf"},
        )
    except ValueError as exc:
        assert "critical risk" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("critical title/authority risk did not block transition")
