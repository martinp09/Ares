from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.commands import router as commands_router
from app.api.runs import router as runs_router
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(commands_router)
    app.include_router(runs_router)
    return TestClient(app)


def test_create_safe_command_returns_created_shape() -> None:
    reset_control_plane_state()
    client = build_client()

    response = client.post(
        "/commands",
        json={
            "business_id": 101,
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-001",
            "payload": {"topic": "houston tired landlords"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["business_id"] == 101
    assert body["deduped"] is False
    assert body["command_type"] == "run_market_research"
    assert body["policy"] == "safe_autonomous"
    assert body["run_id"] is not None
    assert body["approval_id"] is None


def test_create_approval_required_command_returns_pending_approval() -> None:
    reset_control_plane_state()
    client = build_client()

    response = client.post(
        "/commands",
        json={
            "business_id": 101,
            "environment": "dev",
            "command_type": "propose_launch",
            "idempotency_key": "cmd-002",
            "payload": {"campaign_id": "camp-1"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["business_id"] == 101
    assert body["policy"] == "approval_required"
    assert body["approval_id"] is not None
    assert body["run_id"] is None


def test_idempotent_command_dedupes_without_duplicate_run() -> None:
    reset_control_plane_state()
    client = build_client()
    payload = {
        "business_id": 101,
        "environment": "dev",
        "command_type": "run_market_research",
        "idempotency_key": "cmd-003",
        "payload": {"topic": "houston absentee owners"},
    }

    first = client.post("/commands", json=payload, headers=AUTH_HEADERS)
    second = client.post("/commands", json=payload, headers=AUTH_HEADERS)

    assert first.status_code == 201
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert second_body["deduped"] is True
    assert first_body["id"] == second_body["id"]
    assert first_body["business_id"] == second_body["business_id"] == 101
    assert first_body["run_id"] == second_body["run_id"]


def test_create_command_rejects_non_integer_business_id() -> None:
    reset_control_plane_state()
    client = build_client()

    response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-004",
            "payload": {"topic": "austin probate"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
