from app.db.campaign_memberships import CampaignMembershipsRepository


def test_record_from_supabase_ignores_storage_timestamps() -> None:
    record = CampaignMembershipsRepository._record_from_supabase(
        {
            "id": 5,
            "business_id": 1,
            "environment": "dev",
            "lead_id": 9,
            "campaign_id": 3,
            "status": "pending",
            "metadata": {},
            "created_at": "2026-04-16T00:00:00+00:00",
            "updated_at": "2026-04-16T00:00:00+00:00",
        }
    )

    assert record.id == "mbr_5"
    assert record.lead_id == "lead_9"
    assert record.campaign_id == "camp_3"

