from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.site_events import router as site_events_router
from app.domains.site_events.service import reset_site_event_ingestion_state


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(site_events_router)
    return TestClient(app)


def test_site_event_ingestion_returns_202() -> None:
    reset_site_event_ingestion_state()
    client = build_client()

    response = client.post(
        "/site-events",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "event_name": "lead_form_submitted",
            "visitor_id": "visitor-123",
            "session_id": "session-456",
            "properties": {"source": "landing_page"},
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["event_name"] == "lead_form_submitted"
