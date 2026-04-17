from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.main import app
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def _assert_response(response, *, status_code: int) -> dict[str, Any]:
    assert response.status_code == status_code, response.text
    return response.json()


def run_lead_machine_smoke() -> dict[str, Any]:
    reset_control_plane_state()
    client = TestClient(app)

    webhook_payload = {
        "business_id": "limitless",
        "environment": "dev",
        "payload": {
            "event_type": "email_sent",
            "timestamp": "2026-04-16T17:00:00Z",
            "campaign_id": "camp_smoke_001",
            "campaign_name": "Probate Smoke",
            "lead_email": "smoke@example.com",
            "email_id": "msg_smoke_001",
            "step": 1,
        },
    }
    first_webhook = _assert_response(
        client.post("/lead-machine/webhooks/instantly", json=webhook_payload, headers=AUTH_HEADERS),
        status_code=200,
    )
    second_webhook = _assert_response(
        client.post("/lead-machine/webhooks/instantly", json=webhook_payload, headers=AUTH_HEADERS),
        status_code=200,
    )

    command_payload = {
        "business_id": "limitless",
        "environment": "dev",
        "command_type": "run_market_research",
        "idempotency_key": "lead-machine-smoke-replay",
        "payload": {"topic": "houston probate smoke"},
    }
    command_response = _assert_response(client.post("/commands", json=command_payload, headers=AUTH_HEADERS), status_code=201)
    replay_response = _assert_response(
        client.post(f"/replays/{command_response['run_id']}", json={"reason": "smoke replay"}, headers=AUTH_HEADERS),
        status_code=201,
    )

    reminder_payload = {
        "business_id": "limitless",
        "environment": "dev",
        "task_id": "task_smoke_001",
        "lead_id": "lead_smoke_001",
        "task_title": "Call lead about probate follow-up",
        "due_at": "2026-04-16T17:00:00Z",
        "status": "open",
        "assigned_to": "sierra",
        "priority": "high",
    }
    first_reminder = _assert_response(
        client.post("/lead-machine/internal/task-reminder-or-overdue", json=reminder_payload, headers=AUTH_HEADERS),
        status_code=200,
    )
    second_reminder = _assert_response(
        client.post("/lead-machine/internal/task-reminder-or-overdue", json=reminder_payload, headers=AUTH_HEADERS),
        status_code=200,
    )

    assert first_webhook["status"] == "processed"
    assert second_webhook["status"] == "duplicate"
    assert command_response["deduped"] is False
    assert replay_response["requires_approval"] is False
    assert replay_response["child_run_id"] is not None
    assert first_reminder["status"] == "reminded"
    assert second_reminder["status"] == "deduped"

    return {
        "duplicate_submission": {
            "first_status": first_webhook["status"],
            "second_status": second_webhook["status"],
            "receipt_id": first_webhook["receipt_id"],
        },
        "replay_safety": {
            "run_id": command_response["run_id"],
            "child_run_id": replay_response["child_run_id"],
            "requires_approval": replay_response["requires_approval"],
        },
        "manual_call_task": {
            "first_status": first_reminder["status"],
            "second_status": second_reminder["status"],
            "reminder_task_id": first_reminder["reminder_task_id"],
        },
    }


def main() -> int:
    result = run_lead_machine_smoke()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
