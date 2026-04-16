from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.models.campaigns import CampaignMembershipRecord, CampaignMembershipStatus


def build_repository() -> CampaignMembershipsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return CampaignMembershipsRepository(client)


def test_upsert_membership_reuses_campaign_and_lead_key() -> None:
    repository = build_repository()

    first = repository.upsert(
        CampaignMembershipRecord(
            business_id="limitless",
            environment="dev",
            campaign_id="camp_123",
            lead_id="lead_123",
        )
    )
    second = repository.upsert(
        CampaignMembershipRecord(
            business_id="limitless",
            environment="dev",
            campaign_id="camp_123",
            lead_id="lead_123",
            status=CampaignMembershipStatus.ACTIVE,
        )
    )

    assert first.id == second.id
    assert second.status == CampaignMembershipStatus.ACTIVE


def test_memberships_are_indexed_by_campaign_and_lead() -> None:
    repository = build_repository()
    membership = repository.upsert(
        CampaignMembershipRecord(
            business_id="limitless",
            environment="dev",
            campaign_id="camp_123",
            lead_id="lead_123",
        )
    )

    assert repository.list_for_campaign("camp_123")[0].id == membership.id
    assert repository.list_for_lead("lead_123")[0].id == membership.id
