from app.services.lead_webhook_service import lead_webhook_service
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_lead_machine_endpoint_surfaces_generated_tasks_timeline_and_filters(client) -> None:
    reset_control_plane_state()

    first = lead_webhook_service.handle_instantly_webhook(
        business_id="limitless",
        environment="dev",
        payload={
            "event_type": "email_sent",
            "timestamp": "2026-04-16T17:00:00Z",
            "campaign_id": "camp_123",
            "campaign_name": "Probate Wave",
            "lead_email": "lane@example.com",
            "email_id": "msg_123",
            "email_subject": "Probate intake",
            "email_html": "<p>Hidden provider html</p>",
            "step": 1,
        },
    )
    second = lead_webhook_service.handle_instantly_webhook(
        business_id="limitless",
        environment="dev",
        payload={
            "event_type": "email_sent",
            "timestamp": "2026-04-16T17:01:00Z",
            "campaign_id": "camp_other",
            "campaign_name": "Other Wave",
            "lead_email": "other@example.com",
            "email_id": "msg_999",
            "step": 1,
        },
    )

    assert first["status"] == "processed"
    assert second["status"] == "processed"

    response = client.get(
        "/mission-control/lead-machine?business_id=limitless&environment=dev&campaign_id=camp_123&limit=1",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {
        "lead_count": 1,
        "task_count": 1,
        "open_task_count": 1,
        "event_count": 1,
        "suppression_count": 0,
    }
    assert len(body["tasks"]) == 1
    assert body["tasks"][0]["lead_id"] == first["lead_id"]
    assert body["tasks"][0]["campaign_id"] == body["timeline"][0]["campaign_id"]
    assert body["tasks"][0]["task_type"] == "manual_call"
    assert body["tasks"][0]["status"] == "open"
    assert body["tasks"][0]["source_event_id"] == first["event_id"]
    assert len(body["timeline"]) == 1
    timeline_entry = body["timeline"][0]
    assert timeline_entry["id"] == first["event_id"]
    assert timeline_entry["business_id"] == "limitless"
    assert timeline_entry["environment"] == "dev"
    assert timeline_entry["lead_id"] == first["lead_id"]
    assert timeline_entry["campaign_id"] == body["tasks"][0]["campaign_id"]
    assert timeline_entry["lead_name"] == "lane@example.com"
    assert timeline_entry["lead_email"] == "lane@example.com"
    assert timeline_entry["event_type"] == "lead.email.sent"
    assert timeline_entry["provider_name"] == "instantly"
    assert timeline_entry["provider_event_id"] == "msg_123"
    assert timeline_entry["provider_receipt_id"] == first["receipt_id"]
    assert timeline_entry["event_timestamp"] == "2026-04-16T17:00:00Z"
    assert timeline_entry["metadata"]["campaign_name"] == "Probate Wave"
    assert timeline_entry["metadata"]["email_subject"] == "Probate intake"
    assert timeline_entry["metadata"]["provider_event_type"] == "email_sent"
    assert timeline_entry["metadata"]["step"] == 1
    assert timeline_entry["metadata"]["trusted"] is False
    assert "provider_payload" not in timeline_entry["metadata"]
    assert "email_html" not in timeline_entry["metadata"]


def test_lead_machine_endpoint_shows_reply_suppression_without_creating_extra_tasks(client) -> None:
    reset_control_plane_state()

    sent = lead_webhook_service.handle_instantly_webhook(
        business_id="limitless",
        environment="dev",
        payload={
            "event_type": "email_sent",
            "timestamp": "2026-04-16T17:00:00Z",
            "campaign_id": "camp_123",
            "campaign_name": "Probate Wave",
            "lead_email": "reply@example.com",
            "email_id": "msg_123",
            "step": 1,
        },
    )
    reply = lead_webhook_service.handle_instantly_webhook(
        business_id="limitless",
        environment="dev",
        payload={
            "event_type": "reply_received",
            "timestamp": "2026-04-16T17:05:00Z",
            "campaign_id": "camp_123",
            "campaign_name": "Probate Wave",
            "lead_email": "reply@example.com",
            "email_id": "msg_124",
            "reply_text": "Please stop emailing me.",
        },
    )

    assert sent["status"] == "processed"
    assert reply["status"] == "processed"
    assert reply["task_id"] is None

    response = client.get(
        f"/mission-control/lead-machine?business_id=limitless&environment=dev&lead_id={sent['lead_id']}",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {
        "lead_count": 1,
        "task_count": 1,
        "open_task_count": 1,
        "event_count": 2,
        "suppression_count": 1,
    }
    assert len(body["tasks"]) == 1
    assert body["tasks"][0]["source_event_id"] == sent["event_id"]
    assert [entry["event_type"] for entry in body["timeline"]] == ["lead.reply.received", "lead.email.sent"]
    assert body["timeline"][0]["id"] == reply["event_id"]
    assert body["timeline"][0]["metadata"]["provider_event_type"] == "reply_received"
    assert body["timeline"][0]["metadata"]["reply_text"] == "Please stop emailing me."
