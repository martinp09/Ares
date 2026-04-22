from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.client import STORE
from app.api.commands import router as commands_router
from app.api.runs import router as runs_router
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(commands_router)
    app.include_router(runs_router)
    return TestClient(app)


def create_published_agent(client) -> tuple[str, str]:
    agent_response = client.post(
        "/agents",
        json={
            "name": "Published Command Agent",
            "config": {"prompt": "Queue once"},
            "host_adapter_kind": "trigger_dev",
        },
        headers=AUTH_HEADERS,
    )
    created = agent_response.json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200
    return agent_id, revision_id


def test_create_safe_command_returns_created_shape() -> None:
    reset_control_plane_state()
    client = build_client()

    response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-001",
            "payload": {"topic": "houston tired landlords"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
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
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "propose_launch",
            "idempotency_key": "cmd-002",
            "payload": {"campaign_id": "camp-1"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["policy"] == "approval_required"
    assert body["approval_id"] is not None
    assert body["run_id"] is None


def test_idempotent_command_dedupes_without_duplicate_run() -> None:
    reset_control_plane_state()
    client = build_client()
    payload = {
        "business_id": "limitless",
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
    assert first_body["run_id"] == second_body["run_id"]


def test_agent_backed_safe_command_retry_dedupes_after_revision_is_archived(client) -> None:
    reset_control_plane_state()
    agent_id, revision_id = create_published_agent(client)
    payload = {
        "business_id": "limitless",
        "environment": "dev",
        "command_type": "run_market_research",
        "idempotency_key": "cmd-003-agent-archived-retry",
        "payload": {"topic": "houston absentee owners"},
        "agent_revision_id": revision_id,
    }

    first = client.post("/commands", json=payload, headers=AUTH_HEADERS)
    archive_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/archive",
        headers=AUTH_HEADERS,
    )
    second = client.post("/commands", json=payload, headers=AUTH_HEADERS)

    assert first.status_code == 201
    assert archive_response.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert second_body["deduped"] is True
    assert second_body["id"] == first_body["id"]
    assert second_body["run_id"] == first_body["run_id"]
    assert len(STORE.commands) == 1
    assert len(STORE.runs) == 1


def test_create_safe_command_with_invalid_agent_revision_fails_closed_before_persisting_queue_records() -> None:
    reset_control_plane_state()
    client = build_client()

    response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-invalid-agent",
            "payload": {"topic": "houston tired landlords"},
            "agent_revision_id": "rev_missing",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Agent revision not found"
    assert STORE.commands == {}
    assert STORE.runs == {}


def test_create_safe_command_with_disabled_adapter_revision_fails_closed_before_persisting_queue_records(client) -> None:
    reset_control_plane_state()
    agent_response = client.post(
        "/agents",
        json={
            "name": "Disabled Command Agent",
            "config": {"prompt": "Do not queue me"},
            "host_adapter_kind": "codex",
        },
        headers=AUTH_HEADERS,
    )
    created = agent_response.json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200

    direct_client = build_client()
    response = direct_client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-disabled-agent",
            "payload": {"topic": "houston tired landlords"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "codex adapter is disabled in this environment"
    assert STORE.commands == {}
    assert STORE.runs == {}
