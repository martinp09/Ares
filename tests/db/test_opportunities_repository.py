from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.opportunities import OpportunitiesRepository
from app.models.opportunities import (
    OpportunityPipelineConfig,
    OpportunityPipelineStageConfig,
    OpportunityRecord,
    OpportunityStage,
    OpportunityStageHistoryRecord,
)


def build_repository() -> OpportunitiesRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return OpportunitiesRepository(client)


def test_upsert_reuses_existing_record_for_same_lead() -> None:
    repository = build_repository()
    first = repository.upsert(
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
            lead_id="lead_1",
        )
    )
    second = repository.upsert(
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
            lead_id="lead_1",
            stage=OpportunityStage.CONTRACT_SENT,
        )
    )

    assert first.id == second.id
    assert second.stage == OpportunityStage.CONTRACT_SENT


def test_list_filters_by_tenant_and_stage() -> None:
    repository = build_repository()
    repository.upsert(
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
            lead_id="lead_1",
        )
    )
    repository.upsert(
        OpportunityRecord(
            business_id="limitless",
            environment="prod",
            source_lane="probate",
            lead_id="lead_2",
        )
    )

    dev_records = repository.list(business_id="limitless", environment="dev")

    assert len(dev_records) == 1
    assert dev_records[0].lead_id == "lead_1"


def test_upsert_keeps_records_separate_across_source_lanes() -> None:
    repository = build_repository()

    probate = repository.upsert(
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
            contact_id="ctc_1",
        )
    )
    lease_option = repository.upsert(
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane="lease_option_inbound",
            contact_id="ctc_1",
        )
    )

    assert probate.id != lease_option.id
    records = repository.list(business_id="limitless", environment="dev")
    assert len(records) == 2


def test_pipeline_configs_upsert_by_lane_and_list_by_scope() -> None:
    repository = build_repository()

    first = repository.upsert_pipeline_config(
        OpportunityPipelineConfig(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
            name="Probate",
            stages=[
                OpportunityPipelineStageConfig(stage=OpportunityStage.QUALIFIED_OPPORTUNITY, label="Qualified", order=0),
                OpportunityPipelineStageConfig(stage=OpportunityStage.TITLE_OPEN, label="Title Open", order=1),
            ],
        )
    )
    second = repository.upsert_pipeline_config(first.model_copy(update={"name": "Probate v2"}))

    assert first.id == second.id
    assert second.name == "Probate v2"
    assert repository.get_active_pipeline_config(business_id="limitless", environment="dev", source_lane="probate") == second
    assert repository.list_pipeline_configs(business_id="limitless", environment="dev") == [second]


def test_stage_history_appends_and_lists_by_opportunity() -> None:
    repository = build_repository()
    opportunity = repository.upsert(
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
            lead_id="lead_1",
        )
    )

    event = repository.append_stage_history(
        OpportunityStageHistoryRecord(
            business_id="limitless",
            environment="dev",
            opportunity_id=opportunity.id or "",
            from_stage=OpportunityStage.QUALIFIED_OPPORTUNITY,
            to_stage=OpportunityStage.TITLE_OPEN,
            reason="opened title",
        )
    )

    assert event.id is not None
    assert repository.list_stage_history(opportunity.id or "") == [event]
