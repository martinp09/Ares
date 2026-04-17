from app.db.provider_webhooks import ProviderWebhooksRepository


def test_record_from_supabase_ignores_storage_timestamps() -> None:
    record = ProviderWebhooksRepository._record_from_supabase(
        {
            "id": 4,
            "business_id": 1,
            "environment": "dev",
            "provider": "instantly",
            "event_type": "reply_received",
            "idempotency_key": "key",
            "payload": {},
            "processed": True,
            "created_at": "2026-04-16T00:00:00+00:00",
            "updated_at": "2026-04-16T00:00:00+00:00",
        }
    )

    assert record.id == "wh_4"
    assert record.provider == "instantly"

