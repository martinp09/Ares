from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.api import marketing as marketing_api
from app.core.config import Settings
from app.db.bookings import BookingsRepository
from app.db.contacts import ContactsRepository
from app.db.messages import MessagesRepository
from app.db.tasks import TasksRepository
from app.main import app
from app.services.booking_service import BookingService
from app.services.inbound_sms_service import InboundSmsService
from app.services.marketing_lead_service import MarketingLeadService
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}
BUSINESS_ID = "limitless"
ENVIRONMENT = "dev"


def _assert_response(response, *, status_code: int) -> dict[str, Any]:
    assert response.status_code == status_code, response.text
    return response.json()


def _count_by_kind(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _store_records(repository: object, attribute: str, *, business_id: str, environment: str) -> list[Any]:
    with repository.client.transaction() as store:
        rows = list(getattr(store, attribute, {}).values())
    return [
        row
        for row in rows
        if row.business_id == business_id and row.environment == environment
    ]


def _no_live_request_sender(outbound_request: dict[str, Any]) -> None:
    raise RuntimeError(f"Live provider request blocked by smoke harness: {outbound_request.get('endpoint')}")


class _NoLiveAppointmentNotifier:
    def send_appointment_confirmation(self, *, lead_id: str) -> dict[str, str | None]:
        return {}


def _safe_smoke_settings() -> Settings:
    return Settings(
        _env_file=None,
        control_plane_backend="memory",
        marketing_backend="memory",
        lead_machine_backend="memory",
        site_events_backend="memory",
        textgrid_account_sid=None,
        textgrid_auth_token=None,
        textgrid_from_number=None,
        textgrid_sms_url=None,
        textgrid_webhook_secret=None,
        textgrid_status_callback_url=None,
        resend_api_key=None,
        resend_from_email=None,
        resend_reply_to_email=None,
        cal_api_key=None,
        cal_booking_url=None,
        cal_webhook_secret=None,
        trigger_secret_key=None,
    )


@contextmanager
def _no_live_marketing_services():
    settings = _safe_smoke_settings()
    original_lead_service = marketing_api.marketing_lead_service
    original_booking_service = marketing_api.booking_service
    original_inbound_sms_service = marketing_api.inbound_sms_service
    marketing_api.marketing_lead_service = MarketingLeadService(
        settings=settings,
        request_sender=_no_live_request_sender,
    )
    marketing_api.booking_service = BookingService(
        settings=settings,
        appointment_notifier=_NoLiveAppointmentNotifier(),
    )
    marketing_api.inbound_sms_service = InboundSmsService(
        settings=settings,
        request_sender=_no_live_request_sender,
    )
    try:
        yield
    finally:
        marketing_api.marketing_lead_service = original_lead_service
        marketing_api.booking_service = original_booking_service
        marketing_api.inbound_sms_service = original_inbound_sms_service


def run_full_stack_cohesion_smoke(*, no_live_sends: bool = True) -> dict[str, Any]:
    if not no_live_sends:
        raise RuntimeError("Live provider smoke is not implemented in this harness; use scripts/smoke_provider_readiness.py first.")

    reset_control_plane_state()
    with _no_live_marketing_services():
        return _run_no_live_stack_smoke(TestClient(app))


def _run_no_live_stack_smoke(client: TestClient) -> dict[str, Any]:
    health = _assert_response(client.get("/health"), status_code=200)
    tools = _assert_response(client.get("/hermes/tools", headers=AUTH_HEADERS), status_code=200)
    assert any(tool["name"] == "run_market_research" for tool in tools["tools"])

    command = _assert_response(
        client.post(
            "/hermes/tools/run_market_research/invoke",
            json={
                "business_id": BUSINESS_ID,
                "environment": ENVIRONMENT,
                "idempotency_key": "full-stack-cohesion-smoke-command",
                "payload": {"topic": "houston lease option smoke"},
            },
            headers=AUTH_HEADERS,
        ),
        status_code=201,
    )
    run_id = command["run_id"]
    assert run_id

    started = _assert_response(
        client.post(
            f"/trigger/callbacks/runs/{run_id}/started",
            json={"trigger_run_id": "trg_full_stack_smoke"},
            headers=AUTH_HEADERS,
        ),
        status_code=200,
    )
    completed = _assert_response(
        client.post(
            f"/trigger/callbacks/runs/{run_id}/completed",
            json={"trigger_run_id": "trg_full_stack_smoke"},
            headers=AUTH_HEADERS,
        ),
        status_code=200,
    )

    lead = _assert_response(
        client.post(
            "/marketing/leads",
            json={
                "business_id": BUSINESS_ID,
                "environment": ENVIRONMENT,
                "first_name": "Ares Smoke",
                "phone": "+15551234567",
                "email": "ares-smoke@example.com",
                "property_address": "123 Runtime Way, Houston, TX",
            },
            headers=AUTH_HEADERS,
        ),
        status_code=201,
    )
    lead_id = lead["lead_id"]

    manual_task = _assert_response(
        client.post(
            "/marketing/internal/manual-call-task",
            json={
                "leadId": lead_id,
                "businessId": BUSINESS_ID,
                "environment": ENVIRONMENT,
                "sequenceDay": 0,
                "reason": "full_stack_smoke_trigger_shape",
            },
            headers=AUTH_HEADERS,
        ),
        status_code=200,
    )

    booking = _assert_response(
        client.post(
            "/marketing/webhooks/calcom",
            json={
                "triggerEvent": "BOOKING_CREATED",
                "payload": {
                    "booking": {
                        "uid": "book_full_stack_smoke",
                        "bookingUrl": f"https://cal.com/booking/{lead_id}?lead_id={lead_id}",
                        "metadata": {"lead_id": lead_id},
                    }
                },
            },
            headers={**AUTH_HEADERS, "x-cal-event-id": "cal_full_stack_smoke"},
        ),
        status_code=200,
    )

    sms = _assert_response(
        client.post(
            "/marketing/webhooks/textgrid",
            json={
                "MessageSid": "sms_full_stack_smoke",
                "From": "+15551234567",
                "To": "+15557654321",
                "Body": "Yes, still interested",
                "business_id": BUSINESS_ID,
                "environment": ENVIRONMENT,
            },
            headers={**AUTH_HEADERS, "x-textgrid-event-id": "sms_full_stack_smoke"},
        ),
        status_code=200,
    )

    dashboard = _assert_response(
        client.get(
            f"/mission-control/dashboard?business_id={BUSINESS_ID}&environment={ENVIRONMENT}",
            headers=AUTH_HEADERS,
        ),
        status_code=200,
    )
    runs = _assert_response(
        client.get(
            f"/mission-control/runs?business_id={BUSINESS_ID}&environment={ENVIRONMENT}",
            headers=AUTH_HEADERS,
        ),
        status_code=200,
    )
    audit = _assert_response(client.get("/audit", headers=AUTH_HEADERS), status_code=200)
    usage = _assert_response(client.get("/usage", headers=AUTH_HEADERS), status_code=200)

    contact = ContactsRepository().get_lead(lead_id)
    assert contact is not None
    assert contact.booking_status == "booked"
    messages = _store_records(
        MessagesRepository(),
        "marketing_message_rows",
        business_id=BUSINESS_ID,
        environment=ENVIRONMENT,
    )
    tasks = TasksRepository().list(business_id=BUSINESS_ID, environment=ENVIRONMENT)
    bookings = _store_records(
        BookingsRepository(),
        "marketing_booking_rows",
        business_id=BUSINESS_ID,
        environment=ENVIRONMENT,
    )
    assert any(
        (message.direction.value if hasattr(message.direction, "value") else message.direction) == "inbound"
        and message.contact_id == lead_id
        for message in messages
    )
    assert any(task.id == manual_task["taskId"] for task in tasks)
    assert any(booking_event.contact_id == lead_id for booking_event in bookings)
    assert any(event["event_type"] == "trigger_run_completed" for event in audit["events"])
    assert usage["summary"]["by_kind"].get("run", 0) >= 1
    mission_control_run = next((item for item in runs.get("runs", []) if item["id"] == run_id), None)
    assert mission_control_run is not None
    assert mission_control_run["status"] == "completed"
    assert mission_control_run["trigger_run_id"] == completed["trigger_run_id"]
    assert dashboard["recent_completed_count"] >= 1
    assert dashboard["active_run_count"] == 0
    assert dashboard["opportunity_count"] is not None and dashboard["opportunity_count"] >= 1

    return {
        "health": health,
        "hermes": {
            "tool_count": len(tools["tools"]),
            "command_id": command["id"],
            "run_id": run_id,
        },
        "trigger": {
            "started_status": started["status"],
            "completed_status": completed["status"],
            "trigger_run_id": completed["trigger_run_id"],
        },
        "lead": {
            "lead_id": lead_id,
            "booking_status": contact.booking_status,
            "booking_url": lead["booking_url"],
        },
        "providers": {
            "calcom_status": booking["status"],
            "textgrid_status": sms["status"],
            "textgrid_action": sms["action"],
            "live_sends": False,
        },
        "mission_control": {
            "active_run_count": dashboard["active_run_count"],
            "opportunity_count": dashboard["opportunity_count"],
            "recent_completed_count": dashboard["recent_completed_count"],
            "run_count": len(runs.get("runs", [])),
            "run_status": mission_control_run["status"],
        },
        "state": {
            "message_count": len(messages),
            "task_count": len(tasks),
            "booking_event_count": len(bookings),
            "audit_by_type": _count_by_kind(audit["events"], "event_type"),
            "usage_by_kind": usage["summary"]["by_kind"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-live-sends", action="store_true", default=False)
    args = parser.parse_args(argv)
    result = run_full_stack_cohesion_smoke(no_live_sends=True)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
