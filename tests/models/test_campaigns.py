from app.models.campaigns import (
    CampaignMembershipRecord,
    CampaignMembershipStatus,
    CampaignRecord,
    CampaignStatus,
)


def test_campaign_record_preserves_provider_config_fields() -> None:
    campaign = CampaignRecord(
        business_id="limitless",
        environment="dev",
        name="Probate Cold Email",
        provider_name="instantly",
        provider_campaign_id="camp_123",
        status=CampaignStatus.ACTIVE,
        campaign_schedule={"timezone": "America/Chicago"},
        sequences=[{"step": 1, "subject": "Checking in"}],
        email_list=["sender@example.com"],
        provider_routing_rules=[{"mailbox": "sender@example.com"}],
    )

    assert campaign.identity_key() == "provider:instantly:camp_123"
    assert campaign.status == CampaignStatus.ACTIVE
    assert campaign.sequences[0]["step"] == 1


def test_campaign_membership_defaults_to_campaign_and_lead_pair_replay_key() -> None:
    membership = CampaignMembershipRecord(
        business_id="limitless",
        environment="dev",
        campaign_id="camp_123",
        lead_id="lead_123",
        status=CampaignMembershipStatus.ACTIVE,
    )

    assert membership.replay_key() == "camp_123:lead_123"
    assert membership.status == CampaignMembershipStatus.ACTIVE
