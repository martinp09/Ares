from app.domains.site_events.service import (
    ingest_site_event,
    list_ingested_site_events,
    reset_site_event_ingestion_state,
)
from app.models.site_events import SiteEventRecord


def test_ingest_site_event_appends_without_mutating_existing_records() -> None:
    reset_site_event_ingestion_state()

    first = SiteEventRecord(
        business_id=101,
        environment="dev",
        event_name="page_view",
        visitor_id="visitor-1",
        session_id="session-1",
        occurred_at="2026-04-13T05:00:00Z",
        idempotency_key="101:dev:visitor-1:page_view:2026-04-13T05:00:00Z",
        payload={"path": "/"},
    )
    second = SiteEventRecord(
        business_id=101,
        environment="dev",
        event_name="lead_form_submitted",
        visitor_id="visitor-1",
        session_id="session-1",
        occurred_at="2026-04-13T05:01:00Z",
        idempotency_key="101:dev:visitor-1:lead_form_submitted:2026-04-13T05:01:00Z",
        payload={"path": "/apply"},
    )

    ingest_site_event(first)
    ingest_site_event(second)

    ingested = list_ingested_site_events()
    assert [event.event_name for event in ingested] == ["page_view", "lead_form_submitted"]
    assert ingested[0].payload == {"path": "/"}


def test_ingest_site_event_dedupes_by_idempotency_key() -> None:
    reset_site_event_ingestion_state()

    event = SiteEventRecord(
        business_id=101,
        environment="dev",
        event_name="page_view",
        visitor_id="visitor-1",
        session_id="session-1",
        occurred_at="2026-04-13T05:00:00Z",
        idempotency_key="101:dev:visitor-1:page_view:2026-04-13T05:00:00Z",
        payload={"path": "/"},
    )

    first = ingest_site_event(event)
    second = ingest_site_event(event)

    assert first.deduped is False
    assert second.deduped is True
    assert first.event_id == second.event_id
    assert len(list_ingested_site_events()) == 1
