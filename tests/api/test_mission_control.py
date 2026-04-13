from datetime import UTC, datetime, timedelta

from app.models.mission_control import (
    MissionControlContactRecord,
    MissionControlMessageRecord,
    MissionControlThreadRecord,
)
from app.services.mission_control_service import mission_control_service
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_dashboard_endpoint_returns_operator_counts(client) -> None:
    reset_control_plane_state()

    active_run_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-dashboard-active",
            "payload": {"topic": "phoenix wholesalers"},
        },
        headers=AUTH_HEADERS,
    )
    assert active_run_response.status_code == 201

    failed_run_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-dashboard-failed",
            "payload": {"topic": "tampa landlords"},
        },
        headers=AUTH_HEADERS,
    )
    failed_run_id = failed_run_response.json()["run_id"]
    client.post(
        f"/trigger/callbacks/runs/{failed_run_id}/failed",
        json={
            "trigger_run_id": "trg_failed_001",
            "error_classification": "provider_timeout",
            "error_message": "worker timed out",
        },
        headers=AUTH_HEADERS,
    )

    approval_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-dashboard-approval",
            "payload": {"campaign_id": "camp_dashboard"},
        },
        headers=AUTH_HEADERS,
    )
    assert approval_response.status_code == 201

    created_agent = client.post(
        "/agents",
        json={"name": "Mission Control Agent", "config": {"prompt": "Supervise runs"}},
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created_agent["agent"]["id"]
    revision_id = created_agent["revisions"][0]["id"]
    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200

    response = client.get(
        "/mission-control/dashboard?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "approval_count": 1,
        "active_run_count": 1,
        "failed_run_count": 1,
        "active_agent_count": 1,
    }


def test_inbox_endpoint_returns_thread_summaries_and_selected_thread_payload(client) -> None:
    reset_control_plane_state()
    base_time = datetime(2026, 4, 13, 19, 30, tzinfo=UTC)

    approval_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-inbox-approval",
            "payload": {"campaign_id": "camp_inbox"},
        },
        headers=AUTH_HEADERS,
    )
    approval_id = approval_response.json()["approval_id"]

    run_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-inbox-run",
            "payload": {"topic": "nashville absentee owners"},
        },
        headers=AUTH_HEADERS,
    )
    run_id = run_response.json()["run_id"]

    selected_thread = mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=2,
            contact=MissionControlContactRecord(
                display_name="Taylor Brooks",
                phone="+15551230001",
                email="taylor@example.com",
            ),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Can you send me the offer details?",
                    created_at=base_time,
                ),
                MissionControlMessageRecord(
                    direction="internal",
                    channel="internal",
                    body="Reply draft needs operator approval before send.",
                    created_at=base_time + timedelta(minutes=3),
                    approval_id=approval_id,
                    run_id=run_id,
                    message_type="note",
                ),
            ],
            requires_approval=True,
            related_run_id=run_id,
            related_approval_id=approval_id,
            context={"stage": "qualified", "next_best_action": "Approve reply draft"},
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=4),
        )
    )
    mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="call",
            status="waiting",
            unread_count=0,
            contact=MissionControlContactRecord(
                display_name="Jordan Lee",
                phone="+15551230002",
            ),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="call",
                    body="Left voicemail after missed callback.",
                    created_at=base_time + timedelta(minutes=1),
                    message_type="voicemail",
                ),
            ],
            context={"stage": "new"},
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=1),
        )
    )

    response = client.get(
        f"/mission-control/inbox?business_id=limitless&environment=dev&selected_thread_id={selected_thread.id}",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {
        "thread_count": 2,
        "unread_count": 2,
        "approval_required_count": 1,
    }
    assert len(body["threads"]) == 2
    assert body["selected_thread_id"] == selected_thread.id
    assert body["selected_thread"]["thread_id"] == selected_thread.id
    assert body["selected_thread"]["contact"]["display_name"] == "Taylor Brooks"
    assert body["selected_thread"]["related_approval_id"] == approval_id
    assert body["selected_thread"]["related_run_id"] == run_id
    assert body["selected_thread"]["context"]["stage"] == "qualified"
    assert body["selected_thread"]["context"]["next_best_action"] == "Approve reply draft"
    assert body["selected_thread"]["context"]["approval_status"] == "pending"
    assert body["selected_thread"]["context"]["run_status"] == "queued"
    assert [message["body"] for message in body["selected_thread"]["messages"]] == [
        "Can you send me the offer details?",
        "Reply draft needs operator approval before send.",
    ]


def test_runs_endpoint_returns_lineage_with_parent_run_id(client) -> None:
    reset_control_plane_state()

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-runs-parent",
            "payload": {"topic": "atlanta probate leads"},
        },
        headers=AUTH_HEADERS,
    )
    parent_run_id = command_response.json()["run_id"]

    replay_response = client.post(
        f"/replays/{parent_run_id}",
        json={"reason": "refresh market snapshot"},
        headers=AUTH_HEADERS,
    )
    assert replay_response.status_code == 201
    child_run_id = replay_response.json()["child_run_id"]

    response = client.get(
        "/mission-control/runs?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    runs_by_id = {run["id"]: run for run in response.json()["runs"]}
    assert parent_run_id in runs_by_id
    assert child_run_id in runs_by_id
    assert runs_by_id[parent_run_id]["parent_run_id"] is None
    assert child_run_id in runs_by_id[parent_run_id]["child_run_ids"]
    assert runs_by_id[child_run_id]["parent_run_id"] == parent_run_id
