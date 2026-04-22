from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.commands import router as commands_router
from app.api.replays import router as replays_router
from app.db.client import STORE
from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(agents_router)
    app.include_router(commands_router)
    app.include_router(approvals_router)
    app.include_router(replays_router)
    return TestClient(app)


def create_published_agent(client) -> tuple[str, str]:
    created = client.post(
        "/agents",
        json={
            "name": "Replay Agent",
            "config": {"prompt": "Replay through the adapter seam"},
            "host_adapter_kind": "trigger_dev",
            "host_adapter_config": {"queue": "priority"},
        },
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200
    return agent_id, revision_id


def test_safe_autonomous_run_can_be_replayed_without_new_approval() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
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


def test_agent_backed_safe_autonomous_replay_dispatches_child_run_through_adapter_seam() -> None:
    reset_control_plane_state()
    client = build_client()
    _, revision_id = create_published_agent(client)

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-agent-replay",
            "payload": {"topic": "san antonio landlords"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]

    initial_dispatches = HostAdapterDispatchesRepository().list()
    assert len(initial_dispatches) == 1
    assert initial_dispatches[0].run_id == run_id
    assert initial_dispatches[0].agent_revision_id == revision_id

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

    dispatches = HostAdapterDispatchesRepository().list()
    assert len(dispatches) == 2
    assert dispatches[1].agent_revision_id == revision_id
    assert dispatches[1].run_id == body["child_run_id"]
    assert dispatches[1].external_reference == body["child_run_id"]


def test_agent_backed_safe_autonomous_replay_fails_cleanly_when_revision_is_no_longer_dispatchable() -> None:
    reset_control_plane_state()
    client = build_client()
    agent_id, revision_id = create_published_agent(client)

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-agent-replay-archived",
            "payload": {"topic": "san antonio landlords"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]

    archive_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/archive",
        headers=AUTH_HEADERS,
    )
    assert archive_response.status_code == 200

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "new market context"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Archived revisions cannot be dispatched"
    assert len(STORE.runs) == 1
    dispatches = HostAdapterDispatchesRepository().list()
    assert len(dispatches) == 1
    assert dispatches[0].run_id == run_id


def test_side_effecting_run_replay_requires_reapproval() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
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
