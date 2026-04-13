from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.hermes_tools import router as hermes_tools_router
from app.services.run_service import reset_control_plane_state


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(hermes_tools_router)
    return TestClient(app)


def test_list_hermes_tools_exposes_marketing_commands() -> None:
    reset_control_plane_state()
    client = build_client()

    response = client.get("/hermes/tools")
    assert response.status_code == 200
    tools = response.json()["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert "run_market_research" in tool_names
    assert "publish_campaign" in tool_names


def test_invoke_hermes_tool_reuses_command_service() -> None:
    reset_control_plane_state()
    client = build_client()

    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "idempotency_key": "cmd-040",
            "payload": {"topic": "austin landlords"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["command_type"] == "run_market_research"
    assert body["policy"] == "safe_autonomous"
