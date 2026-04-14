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
    base_time = datetime(2026, 4, 13, 20, 15, tzinfo=UTC)

    active_run_response = client.post(
        "/commands",
        json={
            "business_id": 101,
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
            "business_id": 101,
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
            "business_id": 101,
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
        json={
            "business_id": "101",
            "environment": "dev",
            "name": "Mission Control Agent",
            "config": {"prompt": "Supervise runs"},
        },
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created_agent["agent"]["id"]
    revision_id = created_agent["revisions"][0]["id"]
    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200

    mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="101",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=2,
            contact=MissionControlContactRecord(
                display_name="Taylor Brooks",
                phone="+15551230001",
            ),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Need the updated numbers before we move forward.",
                    created_at=base_time,
                ),
            ],
            context={"stage": "qualified"},
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=1),
        )
    )

    response = client.get(
        "/mission-control/dashboard?business_id=101&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "approval_count": 1,
        "active_run_count": 1,
        "failed_run_count": 1,
        "active_agent_count": 1,
        "unread_conversation_count": 1,
        "busy_channel_count": 1,
        "recent_completed_count": 0,
        "system_status": "degraded",
        "updated_at": body["updated_at"],
    }
    assert datetime.fromisoformat(body["updated_at"]) >= base_time + timedelta(minutes=1)


def test_inbox_endpoint_returns_thread_summaries_and_selected_thread_payload(client) -> None:
    reset_control_plane_state()
    base_time = datetime(2026, 4, 13, 19, 30, tzinfo=UTC)

    approval_response = client.post(
        "/commands",
        json={
            "business_id": 101,
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
            "business_id": 101,
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
            business_id="101",
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
            business_id="101",
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
        f"/mission-control/inbox?business_id=101&environment=dev&selected_thread_id={selected_thread.id}",
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
            "business_id": 101,
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
        "/mission-control/runs?business_id=101&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    runs_by_id = {run["id"]: run for run in response.json()["runs"]}
    assert parent_run_id in runs_by_id
    assert child_run_id in runs_by_id
    assert runs_by_id[parent_run_id]["parent_run_id"] is None
    assert child_run_id in runs_by_id[parent_run_id]["child_run_ids"]
    assert runs_by_id[child_run_id]["parent_run_id"] == parent_run_id


def test_approvals_endpoint_returns_pending_queue_with_scope_filters(client) -> None:
    reset_control_plane_state()

    pending_response = client.post(
        "/commands",
        json={
            "business_id": 101,
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-approvals-pending",
            "payload": {"campaign_id": "camp_pending"},
        },
        headers=AUTH_HEADERS,
    )
    pending_approval_id = pending_response.json()["approval_id"]

    approved_response = client.post(
        "/commands",
        json={
            "business_id": 101,
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-approvals-approved",
            "payload": {"campaign_id": "camp_approved"},
        },
        headers=AUTH_HEADERS,
    )
    approved_approval_id = approved_response.json()["approval_id"]
    approve_response = client.post(
        f"/approvals/{approved_approval_id}/approve",
        json={"actor_id": "operator_mc"},
        headers=AUTH_HEADERS,
    )
    assert approve_response.status_code == 200

    other_business_response = client.post(
        "/commands",
        json={
            "business_id": 202,
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-approvals-other-business",
            "payload": {"campaign_id": "camp_other"},
        },
        headers=AUTH_HEADERS,
    )
    assert other_business_response.status_code == 201

    response = client.get(
        "/mission-control/approvals?business_id=101&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert list(body.keys()) == ["approvals"]
    assert len(body["approvals"]) == 1
    assert body["approvals"][0]["id"] == pending_approval_id
    assert body["approvals"][0]["status"] == "pending"
    assert body["approvals"][0]["business_id"] == "101"
    assert body["approvals"][0]["environment"] == "dev"
    assert body["approvals"][0]["command_type"] == "publish_campaign"


def test_agents_endpoint_returns_agent_registry_read_model(client) -> None:
    reset_control_plane_state()

    published_agent = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Published Agent",
            "description": "Runs live",
            "config": {"prompt": "Do live work"},
        },
        headers=AUTH_HEADERS,
    ).json()
    published_agent_id = published_agent["agent"]["id"]
    published_revision_id = published_agent["revisions"][0]["id"]
    publish_response = client.post(
        f"/agents/{published_agent_id}/revisions/{published_revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200

    draft_agent = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Draft Agent",
            "description": "Still drafting",
            "config": {"prompt": "Draft flow"},
        },
        headers=AUTH_HEADERS,
    ).json()
    draft_agent_id = draft_agent["agent"]["id"]

    other_agent = client.post(
        "/agents",
        json={
            "business_id": "other-business",
            "environment": "dev",
            "name": "Other Agent",
            "config": {"prompt": "Stay isolated"},
        },
        headers=AUTH_HEADERS,
    ).json()

    response = client.get(
        "/mission-control/agents?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert list(body.keys()) == ["agents"]
    agents_by_id = {agent["id"]: agent for agent in body["agents"]}
    assert published_agent_id in agents_by_id
    assert draft_agent_id in agents_by_id
    assert other_agent["agent"]["id"] not in agents_by_id
    assert agents_by_id[published_agent_id]["business_id"] == "limitless"
    assert agents_by_id[published_agent_id]["environment"] == "dev"
    assert agents_by_id[published_agent_id]["active_revision_state"] == "published"
    assert agents_by_id[draft_agent_id]["active_revision_id"] is None
    assert agents_by_id[draft_agent_id]["active_revision_state"] == "draft"


def test_assets_endpoint_returns_settings_assets_read_model_and_supports_agent_filter(client) -> None:
    reset_control_plane_state()

    primary_agent = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Primary Agent",
            "config": {"prompt": "Operate inbox"},
        },
        headers=AUTH_HEADERS,
    ).json()
    primary_agent_id = primary_agent["agent"]["id"]

    secondary_agent = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Secondary Agent",
            "config": {"prompt": "Backup flows"},
        },
        headers=AUTH_HEADERS,
    ).json()
    secondary_agent_id = secondary_agent["agent"]["id"]

    cross_scope_agent = client.post(
        "/agents",
        json={
            "business_id": "other-business",
            "environment": "dev",
            "name": "Cross Scope Agent",
            "config": {"prompt": "Do not leak"},
        },
        headers=AUTH_HEADERS,
    ).json()

    unbound_asset = client.post(
        "/agent-assets",
        json={
            "agent_id": primary_agent_id,
            "asset_type": "calendar",
            "label": "Primary Calendar",
            "metadata": {"provider": "cal.com"},
        },
        headers=AUTH_HEADERS,
    ).json()
    bound_asset = client.post(
        "/agent-assets",
        json={
            "agent_id": primary_agent_id,
            "asset_type": "inbox",
            "label": "Leads Inbox",
            "metadata": {"provider": "gmail"},
        },
        headers=AUTH_HEADERS,
    ).json()
    bind_response = client.post(
        f"/agent-assets/{bound_asset['id']}/bind",
        json={"binding_reference": "inbox_ops_001", "metadata": {"address": "ops@example.com"}},
        headers=AUTH_HEADERS,
    )
    assert bind_response.status_code == 200

    other_agent_asset = client.post(
        "/agent-assets",
        json={
            "agent_id": secondary_agent_id,
            "asset_type": "webhook",
            "label": "Secondary Hook",
            "metadata": {"url": "https://example.com/hook"},
        },
        headers=AUTH_HEADERS,
    ).json()

    cross_scope_asset = client.post(
        "/agent-assets",
        json={
            "agent_id": cross_scope_agent["agent"]["id"],
            "asset_type": "form",
            "label": "Other Scope Form",
            "metadata": {"provider": "tally"},
        },
        headers=AUTH_HEADERS,
    ).json()

    response = client.get(
        f"/mission-control/settings/assets?agent_id={primary_agent_id}&business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert list(body.keys()) == ["assets"]
    asset_ids = {asset["id"] for asset in body["assets"]}
    assert unbound_asset["id"] in asset_ids
    assert bound_asset["id"] in asset_ids
    assert other_agent_asset["id"] not in asset_ids
    assert cross_scope_asset["id"] not in asset_ids

    assets_by_id = {asset["id"]: asset for asset in body["assets"]}
    assert assets_by_id[unbound_asset["id"]]["business_id"] == "limitless"
    assert assets_by_id[unbound_asset["id"]]["environment"] == "dev"
    assert assets_by_id[unbound_asset["id"]]["status"] == "unbound"
    assert assets_by_id[unbound_asset["id"]]["connect_later"] is True
    assert assets_by_id[bound_asset["id"]]["status"] == "bound"
    assert assets_by_id[bound_asset["id"]]["connect_later"] is False
