from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.commands import router as commands_router
from app.api.replays import router as replays_router
from app.api.runs import router as runs_router
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(commands_router)
    app.include_router(runs_router)
    app.include_router(replays_router)
    return TestClient(app)


def test_get_run_returns_normalized_state_and_summaries() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": 101,
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-020",
            "payload": {"topic": "dallas wholesalers"},
        },
        headers=AUTH_HEADERS,
    )
    run_id = command_response.json()["run_id"]

    response = client.get(f"/runs/{run_id}", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run_id
    assert body["business_id"] == 101
    assert body["replay_source_run_id"] is None
    assert body["command_policy"] == "safe_autonomous"
    assert isinstance(body["artifacts"], list)
    assert isinstance(body["events"], list)


def test_replayed_child_run_exposes_replay_source_run_id() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": 101,
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-021",
            "payload": {"topic": "el paso owners"},
        },
        headers=AUTH_HEADERS,
    )
    parent_run_id = command_response.json()["run_id"]

    replay_response = client.post(
        f"/replays/{parent_run_id}",
        json={"reason": "refresh data"},
        headers=AUTH_HEADERS,
    )
    child_run_id = replay_response.json()["child_run_id"]

    response = client.get(f"/runs/{child_run_id}", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["parent_run_id"] == parent_run_id
    assert body["replay_source_run_id"] == parent_run_id
