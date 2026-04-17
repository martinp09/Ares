from app.db.lead_events import LeadEventsRepository


def test_record_from_supabase_ignores_storage_created_at() -> None:
    record = LeadEventsRepository._record_from_supabase(
        {
            "id": 8,
            "business_id": 1,
            "environment": "dev",
            "lead_id": 3,
            "event_type": "lead.reply.received",
            "event_timestamp": "2026-04-16T00:00:00+00:00",
            "received_at": "2026-04-16T00:00:00+00:00",
            "idempotency_key": "key",
            "payload": {},
            "metadata": {},
            "created_at": "2026-04-16T00:00:00+00:00",
        }
    )

    assert record.id == "levt_8"
    assert record.lead_id == "lead_3"
    assert record.event_type == "lead.reply.received"

