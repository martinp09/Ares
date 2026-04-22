from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.approvals import router as approvals_router
from app.api.commands import router as commands_router
from app.api.replays import router as replays_router
from app.db.client import STORE
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, actor_id: str, actor_type: str = "user", org_id: str = "org_internal") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(commands_router)
    app.include_router(approvals_router)
    app.include_router(replays_router)
    return TestClient(app)


def test_approve_pending_command_creates_run() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-010",
            "payload": {"campaign_id": "camp-2"},
        },
        headers=AUTH_HEADERS,
    )
    approval_id = command_response.json()["approval_id"]

    response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor_id": "hermes-operator"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approval"]["status"] == "approved"
    assert body["run_id"] is not None


def test_approving_replay_approval_creates_lineage_bound_child_run() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-010-replay-lineage",
            "payload": {"campaign_id": "camp-2"},
        },
        headers=AUTH_HEADERS,
    )
    command_body = command_response.json()
    original_command_id = command_body["id"]
    original_approval_id = command_body["approval_id"]

    approval_response = client.post(
        f"/approvals/{original_approval_id}/approve",
        json={"actor_id": "hermes-operator"},
        headers=AUTH_HEADERS,
    )
    assert approval_response.status_code == 200
    original_run_id = approval_response.json()["run_id"]
    assert original_run_id is not None

    replay_response = client.post(
        f"/replays/{original_run_id}",
        json={"reason": "rerun delivery"},
        headers=org_actor_headers(actor_id="ops-requester"),
    )
    assert replay_response.status_code == 409
    replay_body = replay_response.json()
    replay_approval_id = replay_body["approval_id"]
    assert replay_approval_id is not None

    approved_replay_response = client.post(
        f"/approvals/{replay_approval_id}/approve",
        json={"actor_id": "ops-approver"},
        headers=AUTH_HEADERS,
    )
    assert approved_replay_response.status_code == 200
    child_run_id = approved_replay_response.json()["run_id"]
    assert child_run_id is not None
    assert child_run_id != original_run_id

    assert STORE.commands[original_command_id].run_id == original_run_id
    child_run = STORE.runs[child_run_id]
    assert child_run.parent_run_id == original_run_id
    assert child_run.replay_reason == "rerun delivery"
    assert child_run.command_id != original_command_id

    parent_events = [
        event for event in STORE.runs[original_run_id].events if event.get("event_type") == "replay_requested"
    ]
    assert len(parent_events) == 1
    assert parent_events[0]["payload"]["approval_id"] == replay_approval_id
    assert parent_events[0]["payload"]["triggering_actor"]["actor_id"] == "ops-requester"
    assert parent_events[0]["payload"]["child_run_id"] is None

    parent_bound_events = [
        event for event in STORE.runs[original_run_id].events if event.get("event_type") == "replay_child_bound"
    ]
    assert len(parent_bound_events) == 1
    assert parent_bound_events[0]["payload"]["approval_id"] == replay_approval_id
    assert parent_bound_events[0]["payload"]["child_run_id"] == child_run_id
    assert parent_bound_events[0]["payload"]["triggering_actor"]["actor_id"] == "ops-requester"

    child_events = [
        event for event in child_run.events if event.get("event_type") == "replay_lineage_bound"
    ]
    assert len(child_events) == 1
    assert child_events[0]["payload"]["parent_run_id"] == original_run_id
    assert child_events[0]["payload"]["replay_reason"] == "rerun delivery"
    assert child_events[0]["payload"]["triggering_actor"]["actor_id"] == "ops-requester"
