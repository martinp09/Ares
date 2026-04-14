from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.approvals import router as approvals_router
from app.api.commands import router as commands_router
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(commands_router)
    app.include_router(approvals_router)
    return TestClient(app)


def test_approve_pending_command_creates_run() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": 101,
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
    assert body["approval"]["business_id"] == 101
    assert body["approval"]["status"] == "approved"
    assert body["run_id"] is not None
