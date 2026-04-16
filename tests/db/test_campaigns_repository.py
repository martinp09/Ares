from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.models.campaigns import CampaignRecord, CampaignStatus


def build_repository() -> CampaignsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return CampaignsRepository(client)


def test_upsert_reuses_campaign_key_and_updates_status() -> None:
    repository = build_repository()

    first = repository.upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Probate",
            provider_name="instantly",
            provider_campaign_id="camp_123",
        )
    )
    second = repository.upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Probate",
            provider_name="instantly",
            provider_campaign_id="camp_123",
            status=CampaignStatus.ACTIVE,
        )
    )

    assert first.id == second.id
    assert second.status == CampaignStatus.ACTIVE


def test_list_filters_by_business_and_environment() -> None:
    repository = build_repository()
    repository.upsert(CampaignRecord(business_id="limitless", environment="dev", name="A"))
    repository.upsert(CampaignRecord(business_id="limitless", environment="prod", name="B"))

    campaigns = repository.list(business_id="limitless", environment="dev")
    assert [campaign.name for campaign in campaigns] == ["A"]
