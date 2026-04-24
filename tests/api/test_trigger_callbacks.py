from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.commands import router as commands_router
from app.api.replays import router as replays_router
from app.api.runs import router as runs_router
from app.api.trigger_callbacks import router as trigger_callbacks_router
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(commands_router)
    app.include_router(replays_router)
    app.include_router(runs_router)
    app.include_router(trigger_callbacks_router)
    return TestClient(app)


def create_safe_run(client: TestClient, *, idempotency_key: str = "cmd-001") -> str:
    response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": idempotency_key,
            "payload": {"topic": "houston tired landlords"},
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 201
    return response.json()["run_id"]


def test_run_started_updates_run_to_in_progress() -> None:
    reset_control_plane_state()
    client = build_client()
    run_id = create_safe_run(client, idempotency_key="cmd-started")

    response = client.post(
        f"/trigger/callbacks/runs/{run_id}/started",
        json={"trigger_run_id": "trg-123"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["event_type"] == "run_started"
    assert body["status"] == "in_progress"

    run_detail = client.get(f"/runs/{run_id}", headers=AUTH_HEADERS)
    assert run_detail.status_code == 200
    detail = run_detail.json()
    assert detail["status"] == "in_progress"
    assert detail["started_at"] is not None
    assert detail["trigger_run_id"] == "trg-123"


def test_run_started_accepts_trigger_runtime_contract_fields() -> None:
    reset_control_plane_state()
    client = build_client()
    run_id = create_safe_run(client, idempotency_key="cmd-started-contract")

    response = client.post(
        f"/trigger/callbacks/runs/{run_id}/started",
        json={
            "trigger_run_id": "trg-contract",
            "command_id": "cmd_contract",
            "business_id": "limitless",
            "environment": "dev",
            "idempotency_key": "cmd-started-contract",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["event_type"] == "run_started"
    assert body["trigger_run_id"] == "trg-contract"


def test_artifact_produced_appends_artifact_rows_without_mutating_prior_artifacts() -> None:
    reset_control_plane_state()
    client = build_client()
    run_id = create_safe_run(client, idempotency_key="cmd-artifacts")

    first = client.post(
        f"/trigger/callbacks/runs/{run_id}/artifacts",
        json={
            "artifact_type": "market_research_report",
            "payload": {"summary": "top neighborhoods"},
        },
        headers=AUTH_HEADERS,
    )
    second = client.post(
        f"/trigger/callbacks/runs/{run_id}/artifacts",
        json={
            "artifact_type": "campaign_brief",
            "payload": {"headline": "tired landlords"},
        },
        headers=AUTH_HEADERS,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["artifact_type"] == "market_research_report"
    assert second_body["artifact_type"] == "campaign_brief"
    assert first_body["artifact_id"] != second_body["artifact_id"]

    run_detail = client.get(f"/runs/{run_id}", headers=AUTH_HEADERS)
    detail = run_detail.json()
    assert len(detail["artifacts"]) == 2
    assert detail["artifacts"][0]["artifact_type"] == "market_research_report"
    assert detail["artifacts"][1]["artifact_type"] == "campaign_brief"


def test_artifact_produced_persists_trigger_run_id_linkage() -> None:
    reset_control_plane_state()
    client = build_client()
    run_id = create_safe_run(client, idempotency_key="cmd-artifact-trigger")

    response = client.post(
        f"/trigger/callbacks/runs/{run_id}/artifacts",
        json={
            "trigger_run_id": "trg-artifact-first",
            "artifact_type": "lead_machine_intake",
            "payload": {"processed_count": 2},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    run_detail = client.get(f"/runs/{run_id}", headers=AUTH_HEADERS)
    assert run_detail.status_code == 200
    assert run_detail.json()["trigger_run_id"] == "trg-artifact-first"


def test_run_completed_sets_status_completed() -> None:
    reset_control_plane_state()
    client = build_client()
    run_id = create_safe_run(client, idempotency_key="cmd-completed")

    started = client.post(
        f"/trigger/callbacks/runs/{run_id}/started",
        json={"trigger_run_id": "trg-456"},
        headers=AUTH_HEADERS,
    )
    assert started.status_code == 200

    completed = client.post(
        f"/trigger/callbacks/runs/{run_id}/completed",
        json={"trigger_run_id": "trg-456"},
        headers=AUTH_HEADERS,
    )

    assert completed.status_code == 200
    body = completed.json()
    assert body["event_type"] == "run_completed"
    assert body["status"] == "completed"

    run_detail = client.get(f"/runs/{run_id}", headers=AUTH_HEADERS)
    detail = run_detail.json()
    assert detail["status"] == "completed"
    assert detail["completed_at"] is not None


def test_run_failed_sets_status_failed_and_stores_error_payload() -> None:
    reset_control_plane_state()
    client = build_client()
    run_id = create_safe_run(client, idempotency_key="cmd-failed")

    started = client.post(
        f"/trigger/callbacks/runs/{run_id}/started",
        json={"trigger_run_id": "trg-789"},
        headers=AUTH_HEADERS,
    )
    assert started.status_code == 200

    failed = client.post(
        f"/trigger/callbacks/runs/{run_id}/failed",
        json={
            "trigger_run_id": "trg-789",
            "error_classification": "tool_error",
            "error_message": "market research timed out",
        },
        headers=AUTH_HEADERS,
    )

    assert failed.status_code == 200
    body = failed.json()
    assert body["event_type"] == "run_failed"
    assert body["status"] == "failed"
    assert body["error_classification"] == "tool_error"

    run_detail = client.get(f"/runs/{run_id}", headers=AUTH_HEADERS)
    detail = run_detail.json()
    assert detail["status"] == "failed"
    assert detail["error_classification"] == "tool_error"
    assert detail["error_message"] == "market research timed out"
