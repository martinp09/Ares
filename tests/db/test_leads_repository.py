from app.db.leads import LeadsRepository


def test_record_from_supabase_ignores_storage_only_columns_and_keeps_probate_link() -> None:
    record = LeadsRepository._record_from_supabase(
        {
            "id": 9,
            "business_id": 1,
            "environment": "dev",
            "identity_key": "email:test@example.com",
            "probate_lead_id": 7,
            "email": "test@example.com",
            "source": "probate_intake",
            "lifecycle_status": "ready",
            "lt_interest_status": "neutral",
            "raw_payload": {},
        }
    )

    assert record.id == "lead_9"
    assert record.email == "test@example.com"
    assert record.raw_payload["probate_lead_id"] == "prob_7"

