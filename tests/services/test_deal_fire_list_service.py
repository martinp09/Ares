from datetime import timedelta

from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore, utc_now
from app.db.deals import DealsRepository
from app.models.deals import (
    Deal,
    DealDocumentRequirement,
    DealRiskFlag,
    DealRiskSeverity,
    DealSourceLane,
    DealStage,
    DealStrategyLane,
    DealTask,
    DealTaskType,
)
from app.services.deal_fire_list_service import DealFireListService


def test_fire_list_includes_ranked_tasks_risks_docs_and_provider_gate_blockers() -> None:
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
    assert deal.id is not None
    repo.upsert_task(
        DealTask(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            task_type=DealTaskType.VERIFY_AUTHORITY,
            title="Verify authority",
            due_at=utc_now() - timedelta(days=1),
        )
    )
    repo.upsert_document_requirement(
        DealDocumentRequirement(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            document_type="letters_testamentary_or_administration",
            required_stage=DealStage.CONTACT_READY,
        )
    )
    repo.upsert_risk_flag(
        DealRiskFlag(
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            code="authority_unverified",
            label="Authority unverified",
            severity=DealRiskSeverity.HIGH,
        )
    )

    items = DealFireListService(deals_repository=repo).get_fire_list(business_id="limitless", environment="dev")

    assert [item.item_type for item in items][:2] == ["risk", "task"]
    assert {item.item_type for item in items} >= {"risk", "task", "document", "provider_gate"}
    provider_item = next(item for item in items if item.item_type == "provider_gate")
    assert provider_item.action_enabled is False
    assert "Provider sends remain disabled" in provider_item.reason
    assert all(item.deal_id == deal.id for item in items)


def test_fire_list_respects_business_environment_scope() -> None:
    store = InMemoryControlPlaneStore()
    repo = DealsRepository(client=InMemoryControlPlaneClient(store))
    in_scope = repo.upsert_deal(
        Deal(
            business_id="limitless",
            environment="dev",
            source_lane=DealSourceLane.LEASE_OPTION_INBOUND,
            strategy_lane=DealStrategyLane.LEASE_OPTION,
            source_record_id="lead_in_scope",
        )
    )
    out_of_scope = repo.upsert_deal(
        Deal(
            business_id="other",
            environment="prod",
            source_lane=DealSourceLane.HARRIS_PROBATE,
            strategy_lane=DealStrategyLane.CURATIVE_TITLE,
            source_record_id="lead_out_scope",
        )
    )
    assert in_scope.id is not None
    assert out_of_scope.id is not None
    repo.upsert_task(
        DealTask(
            business_id=in_scope.business_id,
            environment=in_scope.environment,
            deal_id=in_scope.id,
            task_type=DealTaskType.CONFIRM_PITI,
            title="Confirm PITI",
            due_at=utc_now() - timedelta(hours=1),
        )
    )
    repo.upsert_task(
        DealTask(
            business_id=out_of_scope.business_id,
            environment=out_of_scope.environment,
            deal_id=out_of_scope.id,
            task_type=DealTaskType.VERIFY_AUTHORITY,
            title="Verify authority",
            due_at=utc_now() - timedelta(hours=1),
        )
    )

    items = DealFireListService(deals_repository=repo).get_fire_list(business_id="limitless", environment="dev")

    assert {item.deal_id for item in items} == {in_scope.id}
