from app.domains.site_events.service import (
    ingest_site_event,
    list_ingested_site_events,
    reset_site_event_ingestion_state,
)
from app.models.site_events import SiteEventRecord


def test_ingest_site_event_appends_without_mutating_existing_records() -> None:
    reset_site_event_ingestion_state()

    first = SiteEventRecord(
        business_id="limitless",
        environment="dev",
        event_name="page_view",
        visitor_id="visitor-1",
        session_id="session-1",
        properties={"path": "/"},
    )
    second = SiteEventRecord(
        business_id="limitless",
        environment="dev",
        event_name="lead_form_submitted",
        visitor_id="visitor-1",
        session_id="session-1",
        properties={"path": "/apply"},
    )

    ingest_site_event(first)
    ingest_site_event(second)

    ingested = list_ingested_site_events()
    assert [event.event_name for event in ingested] == ["page_view", "lead_form_submitted"]
    assert ingested[0].properties == {"path": "/"}
