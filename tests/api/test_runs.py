from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.commands import router as commands_router
from app.api.runs import router as runs_router
from app.services.run_service import reset_control_plane_state


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(commands_router)
    app.include_router(runs_router)
    return TestClient(app)


def test_get_run_returns_normalized_state_and_summaries() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-020",
            "payload": {"topic": "dallas wholesalers"},
        },
    )
    run_id = command_response.json()["run_id"]

    response = client.get(f"/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run_id
    assert body["command_policy"] == "safe_autonomous"
    assert isinstance(body["artifacts"], list)
    assert isinstance(body["events"], list)
