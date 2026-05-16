from datetime import timedelta

from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore, reset_control_plane_store, utc_now
from app.db.deals import DealsRepository
from app.models.deals import (
    Deal,
    DealAuditEvent,
    DealAuditEventType,
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
    DealTaskStatus,
    DealTaskType,
)


def _repo() -> tuple[DealsRepository, InMemoryControlPlaneStore]:
    store = InMemoryControlPlaneStore()
    return DealsRepository(client=InMemoryControlPlaneClient(store)), store


def _deal() -> Deal:
    return Deal(
        business_id="limitless",
        environment="dev",
        source_lane=DealSourceLane.HARRIS_PROBATE,
        strategy_lane=DealStrategyLane.CURATIVE_TITLE,
        source_record_id="lead_341",
        property_address="123 Main St",
    )


def test_upsert_deal_is_idempotent_by_source_identity() -> None:
    repo, _store = _repo()

    first = repo.upsert_deal(_deal())
    second = repo.upsert_deal(_deal().model_copy(update={"property_address": "123 Main Street"}))

    assert first.id == second.id
    assert second.property_address == "123 Main Street"
    assert len(repo.list_deals(business_id="limitless", environment="dev")) == 1


def test_repository_persists_deal_detail_children_in_memory() -> None:
    repo, _store = _repo()
    deal = repo.upsert_deal(_deal())
    assert deal.id is not None

    party = repo.add_party(
        DealParty(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            name="Jane Applicant",
            role=DealPartyRole.CONTACT_CANDIDATE,
        )
    )
    task = repo.upsert_task(
        DealTask(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            task_type=DealTaskType.VERIFY_AUTHORITY,
            title="Verify seller authority",
            due_at=utc_now() - timedelta(days=1),
        )
    )
    requirement = repo.upsert_document_requirement(
        DealDocumentRequirement(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            document_type="letters_testamentary",
            required_stage=DealStage.CONTACT_READY,
        )
    )
    risk = repo.upsert_risk_flag(
        DealRiskFlag(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            code="authority_unverified",
            label="Authority unverified",
            severity=DealRiskSeverity.HIGH,
        )
    )
    stage_event = repo.add_stage_event(
        DealStageEvent(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            from_stage=None,
            to_stage=DealStage.QUALIFIED,
        )
    )
    audit = repo.add_audit_event(
        DealAuditEvent(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            event_type=DealAuditEventType.DEAL_PROMOTED,
            actor_id="operator",
        )
    )

    detail = repo.get_detail(deal.id)

    assert detail is not None
    assert detail.deal.id == deal.id
    assert [row.id for row in detail.parties] == [party.id]
    assert [row.id for row in detail.tasks] == [task.id]
    assert [row.id for row in detail.document_requirements] == [requirement.id]
    assert [row.id for row in detail.risk_flags] == [risk.id]
    assert [row.id for row in detail.stage_events] == [stage_event.id]
    assert [row.id for row in detail.audit_events] == [audit.id]


def test_repository_lists_and_filters_deals_by_scope_stage_and_lane() -> None:
    repo, _store = _repo()
    repo.upsert_deal(_deal())
    repo.upsert_deal(
        Deal(
            business_id="limitless",
            environment="dev",
            source_lane=DealSourceLane.LEASE_OPTION_INBOUND,
            strategy_lane=DealStrategyLane.LEASE_OPTION,
            stage=DealStage.CONTACT_READY,
            source_record_id="lead_lease",
        )
    )
    repo.upsert_deal(
        Deal(
            business_id="other",
            environment="prod",
            source_lane=DealSourceLane.HARRIS_PROBATE,
            strategy_lane=DealStrategyLane.CURATIVE_TITLE,
            source_record_id="lead_other",
        )
    )

    assert len(repo.list_deals(business_id="limitless", environment="dev")) == 2
    assert [deal.strategy_lane for deal in repo.list_deals(strategy_lane=DealStrategyLane.LEASE_OPTION)] == [
        DealStrategyLane.LEASE_OPTION
    ]
    assert [deal.stage for deal in repo.list_deals(stage=DealStage.CONTACT_READY)] == [DealStage.CONTACT_READY]


def test_reset_control_plane_store_clears_deal_state() -> None:
    store = InMemoryControlPlaneStore()
    repo = DealsRepository(client=InMemoryControlPlaneClient(store))
    repo.upsert_deal(_deal())

    reset_control_plane_store(store)

    assert repo.list_deals() == []
    assert store.deal_keys == {}
