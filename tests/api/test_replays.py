from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.approvals import router as approvals_router
from app.api.commands import router as commands_router
from app.api.replays import router as replays_router
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(commands_router)
    app.include_router(approvals_router)
    app.include_router(replays_router)
    return TestClient(app)


def test_safe_autonomous_run_can_be_replayed_without_new_approval() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": 101,
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030",
            "payload": {"topic": "san antonio landlords"},
        },
        headers=AUTH_HEADERS,
    )
    run_id = command_response.json()["run_id"]

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "new market context"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["requires_approval"] is False
    assert body["parent_run_id"] == run_id
    assert body["child_run_id"] is not None


def test_side_effecting_run_replay_requires_reapproval() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": 101,
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-031",
            "payload": {"campaign_id": "camp-3"},
        },
        headers=AUTH_HEADERS,
    )
    approval_id = command_response.json()["approval_id"]
    approval_response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor_id": "ops-1"},
        headers=AUTH_HEADERS,
    )
    run_id = approval_response.json()["run_id"]

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "rerun delivery"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 409
    body = response.json()
    assert body["requires_approval"] is True
    assert body["approval_id"] is not None
