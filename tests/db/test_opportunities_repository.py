from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.opportunities import OpportunitiesRepository
from app.models.opportunities import OpportunityRecord, OpportunityStage


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
