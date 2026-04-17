from app.db.suppression import SuppressionRepository


def test_record_from_supabase_ignores_scope_key_storage_column() -> None:
    record = SuppressionRepository._record_from_supabase(
        {
            "id": 6,
            "business_id": 1,
            "environment": "dev",
            "lead_id": 9,
            "scope": "global",
            "scope_key": "global:lead_9",
            "reason": "reply_received",
            "source": "webhook",
            "active": True,
            "metadata": {},
        }
    )

    assert record.id == "sup_6"
    assert record.lead_id == "lead_9"
    assert record.reason == "reply_received"

