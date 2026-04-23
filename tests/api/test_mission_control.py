from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.models.host_adapters import HostAdapterKind
from app.models.mission_control import (
    MissionControlContactRecord,
    MissionControlMessageRecord,
    MissionControlThreadRecord,
)
from app.models.campaigns import CampaignMembershipRecord, CampaignMembershipStatus, CampaignRecord, CampaignStatus
from app.models.leads import LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType
from app.services.mission_control_service import mission_control_service
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def create_published_agent(
    client,
    *,
    headers: dict[str, str],
    name: str,
    business_id: str = "limitless",
    environment: str = "dev",
    host_adapter_kind: str = HostAdapterKind.TRIGGER_DEV.value,
    compatibility_metadata: dict | None = None,
    release_channel: str | None = None,
) -> tuple[str, str]:
    payload = {
        "business_id": business_id,
        "environment": environment,
        "name": name,
        "config": {"prompt": f"{name} prompt"},
        "host_adapter_kind": host_adapter_kind,
    }
    if compatibility_metadata is not None:
        payload["compatibility_metadata"] = compatibility_metadata
    if release_channel is not None:
        payload["release_channel"] = release_channel
    created = client.post(
        "/agents",
        json=payload,
        headers=headers,
    )
    assert created.status_code == 200
    created_body = created.json()
    agent_id = created_body["agent"]["id"]
    revision_id = created_body["revisions"][0]["id"]
    publish_response = client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=headers)
    assert publish_response.status_code == 200
    return agent_id, revision_id


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
        json={
            "business_id": "limitless",
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

    out_of_scope_agent = client.post(
        "/agents",
        json={
            "business_id": "otherco",
            "environment": "prod",
            "name": "Out of scope Agent",
            "config": {"prompt": "Ignore this one"},
        },
        headers=AUTH_HEADERS,
    ).json()
    other_agent_id = out_of_scope_agent["agent"]["id"]
    other_revision_id = out_of_scope_agent["revisions"][0]["id"]
    other_publish_response = client.post(
        f"/agents/{other_agent_id}/revisions/{other_revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert other_publish_response.status_code == 200

    response = client.get(
        "/mission-control/dashboard?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    body = response.json()
    assert body["approval_count"] == 1
    assert body["active_run_count"] == 1
    assert body["failed_run_count"] == 1
    assert body["active_agent_count"] == 1
    assert body["busy_channel_count"] >= 0
    assert body["recent_completed_count"] >= 0
    assert body["system_status"] in {"healthy", "watch", "degraded"}
    assert "outbound_probate_summary" not in body
    assert "inbound_lease_option_summary" not in body
    assert "opportunity_pipeline_summary" not in body
    assert "updated_at" in body


def test_dashboard_endpoint_hides_other_org_records_with_same_scope(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")
    base_time = datetime(2026, 4, 18, 9, 0, tzinfo=UTC)

    alpha_run = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-dashboard-alpha-run",
            "payload": {"topic": "alpha leads", "org_id": "org_alpha"},
        },
        headers=AUTH_HEADERS,
    )
    assert alpha_run.status_code == 201

    beta_run = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-dashboard-beta-run",
            "payload": {"topic": "beta leads", "org_id": "org_beta"},
        },
        headers=AUTH_HEADERS,
    )
    beta_run_id = beta_run.json()["run_id"]
    failed_beta = client.post(
        f"/trigger/callbacks/runs/{beta_run_id}/failed",
        json={
            "trigger_run_id": "trg_beta_failed_001",
            "error_classification": "provider_timeout",
            "error_message": "worker timed out",
        },
        headers=AUTH_HEADERS,
    )
    assert failed_beta.status_code == 200

    alpha_approval = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-dashboard-alpha-approval",
            "payload": {"campaign_id": "camp_alpha", "org_id": "org_alpha"},
        },
        headers=AUTH_HEADERS,
    )
    assert alpha_approval.status_code == 201

    beta_approval = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-dashboard-beta-approval",
            "payload": {"campaign_id": "camp_beta", "org_id": "org_beta"},
        },
        headers=AUTH_HEADERS,
    )
    assert beta_approval.status_code == 201

    create_published_agent(client, headers=alpha_headers, name="Alpha Mission Control Agent")
    create_published_agent(client, headers=beta_headers, name="Beta Mission Control Agent")

    mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=1,
            contact=MissionControlContactRecord(display_name="Alpha Lead", phone="+155****0101"),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Alpha follow-up",
                    created_at=base_time,
                )
            ],
            context={"org_id": "org_alpha", "booking_status": "pending"},
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=1),
        )
    )
    mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=3,
            contact=MissionControlContactRecord(display_name="Beta Lead", phone="+155****0202"),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Beta follow-up",
                    created_at=base_time,
                )
            ],
            context={"org_id": "org_beta", "booking_status": "pending"},
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=2),
        )
    )

    alpha_response = client.get(
        "/mission-control/dashboard?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )
    beta_response = client.get(
        "/mission-control/dashboard?business_id=limitless&environment=dev",
        headers=beta_headers,
    )

    assert alpha_response.status_code == 200
    assert beta_response.status_code == 200
    alpha_body = alpha_response.json()
    beta_body = beta_response.json()
    assert alpha_body["approval_count"] == 1
    assert alpha_body["active_run_count"] == 1
    assert alpha_body["failed_run_count"] == 0
    assert alpha_body["active_agent_count"] == 1
    assert alpha_body["unread_conversation_count"] == 1
    assert beta_body["approval_count"] == 1
    assert beta_body["active_run_count"] == 0
    assert beta_body["failed_run_count"] == 1
    assert beta_body["active_agent_count"] == 1
    assert beta_body["unread_conversation_count"] == 1


def test_dashboard_endpoint_changes_with_org_header_even_when_business_and_environment_match(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    alpha_run = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-dashboard-header-alpha",
            "payload": {"topic": "alpha leads", "org_id": "org_alpha"},
        },
        headers=AUTH_HEADERS,
    )
    assert alpha_run.status_code == 201

    beta_run = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-dashboard-header-beta",
            "payload": {"topic": "beta leads", "org_id": "org_beta"},
        },
        headers=AUTH_HEADERS,
    )
    assert beta_run.status_code == 201
    failed_beta = client.post(
        f"/trigger/callbacks/runs/{beta_run.json()['run_id']}/failed",
        json={
            "trigger_run_id": "trg_header_beta_failed_001",
            "error_classification": "provider_timeout",
            "error_message": "worker timed out",
        },
        headers=AUTH_HEADERS,
    )
    assert failed_beta.status_code == 200

    alpha_response = client.get(
        "/mission-control/dashboard?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )
    beta_response = client.get(
        "/mission-control/dashboard?business_id=limitless&environment=dev",
        headers=beta_headers,
    )

    assert alpha_response.status_code == 200
    assert beta_response.status_code == 200
    assert alpha_response.json()["active_run_count"] == 1
    assert beta_response.json()["active_run_count"] == 0
    assert alpha_response.json()["failed_run_count"] == 0
    assert beta_response.json()["failed_run_count"] == 1


def test_agents_endpoint_filters_to_requested_scope(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    alpha_agent_id, _ = create_published_agent(client, headers=alpha_headers, name="Alpha Agent")
    create_published_agent(client, headers=beta_headers, name="Beta Agent")

    response = client.get(
        "/mission-control/agents?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["agents"]) == 1
    assert body["agents"][0]["id"] == alpha_agent_id


def test_agents_endpoint_exposes_release_rollback_and_eval_state(client) -> None:
    reset_control_plane_state()

    agent_id, first_revision_id = create_published_agent(
        client,
        headers=AUTH_HEADERS,
        name="Release Read Model Agent",
        release_channel="dogfood",
    )

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{first_revision_id}/clone",
        headers=AUTH_HEADERS,
    )
    assert clone_response.status_code == 200
    second_revision_id = clone_response.json()["revisions"][-1]["id"]

    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{second_revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200

    rollback_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/rollback",
        json={
            "notes": "Rollback to known-good revision",
            "rollback_reason": "Operator reported a production regression after promotion",
            "evaluation_summary": {
                "outcome_name": "rollback_assessment",
                "artifact_type": "agent_revision",
                "artifact_payload": {"target_revision_id": first_revision_id},
                "rubric_criteria": ["known good revision exists", "regression isolated"],
                "evaluator_result": "Rollback is required to restore the stable release.",
                "passed": False,
                "failure_details": ["Promoted revision regressed production behavior"],
            },
        },
        headers=AUTH_HEADERS,
    )
    assert rollback_response.status_code == 200
    rollback_body = rollback_response.json()
    rollback_active_revision_id = rollback_body["agent"]["active_revision_id"]

    response = client.get(
        "/mission-control/agents?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["agents"]) == 1
    release = body["agents"][0]["release"]
    assert release == {
        "event_id": rollback_body["event"]["id"],
        "event_type": "rollback",
        "release_channel": "dogfood",
        "created_at": rollback_body["event"]["created_at"],
        "previous_active_revision_id": second_revision_id,
        "target_revision_id": first_revision_id,
        "resulting_active_revision_id": rollback_active_revision_id,
        "rollback_source_revision_id": first_revision_id,
        "evaluation": {
            "outcome_id": rollback_body["event"]["evaluation_summary"]["outcome_id"],
            "outcome_name": "rollback_assessment",
            "status": "failed",
            "satisfied": False,
            "evaluator_result": "Rollback is required to restore the stable release.",
            "failure_details": ["Promoted revision regressed production behavior"],
            "rubric_criteria": ["known good revision exists", "regression isolated"],
            "require_passing_evaluation": False,
            "blocked_promotion": False,
            "rollback_reason": "Operator reported a production regression after promotion",
        },
    }


def test_agents_endpoint_exposes_host_adapter_descriptor_data(client) -> None:
    reset_control_plane_state()

    enabled_agent_id, enabled_revision_id = create_published_agent(
        client,
        headers=AUTH_HEADERS,
        name="Enabled Host Adapter Agent",
        host_adapter_kind=HostAdapterKind.TRIGGER_DEV.value,
    )
    disabled_agent_id, disabled_revision_id = create_published_agent(
        client,
        headers=AUTH_HEADERS,
        name="Disabled Host Adapter Agent",
        host_adapter_kind=HostAdapterKind.CODEX.value,
    )

    response = client.get(
        "/mission-control/agents?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    agents_by_id = {agent["id"]: agent for agent in response.json()["agents"]}

    assert agents_by_id[enabled_agent_id]["active_revision_id"] == enabled_revision_id
    assert agents_by_id[enabled_agent_id]["host_adapter"] == {
        "kind": "trigger_dev",
        "enabled": True,
        "display_name": "Trigger.dev",
        "adapter_details_label": "Adapter details",
        "capabilities": {
            "dispatch": True,
            "status_correlation": True,
            "artifact_reporting": True,
            "cancellation": False,
        },
        "disabled_reason": None,
    }

    assert agents_by_id[disabled_agent_id]["active_revision_id"] == disabled_revision_id
    assert agents_by_id[disabled_agent_id]["host_adapter"] == {
        "kind": "codex",
        "enabled": False,
        "display_name": "Codex",
        "adapter_details_label": "Adapter details",
        "capabilities": {
            "dispatch": False,
            "status_correlation": False,
            "artifact_reporting": False,
            "cancellation": False,
        },
        "disabled_reason": "codex adapter is disabled in this environment",
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
                phone="+155****0001",
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
                phone="+155****0002",
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


def test_inbox_endpoint_hides_other_org_threads_with_same_scope(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    base_time = datetime(2026, 4, 13, 20, 0, tzinfo=UTC)

    alpha_thread = mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=1,
            contact=MissionControlContactRecord(display_name="Alpha Prospect", phone="+155****0303"),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Alpha thread",
                    created_at=base_time,
                )
            ],
            context={"org_id": "org_alpha", "stage": "qualified"},
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=1),
        )
    )
    beta_thread = mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=2,
            contact=MissionControlContactRecord(display_name="Beta Prospect", phone="+155****0404"),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Beta thread",
                    created_at=base_time,
                )
            ],
            context={"org_id": "org_beta", "stage": "new"},
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=2),
        )
    )

    alpha_response = client.get(
        f"/mission-control/inbox?business_id=limitless&environment=dev&selected_thread_id={alpha_thread.id}",
        headers=alpha_headers,
    )
    hidden_response = client.get(
        f"/mission-control/inbox?business_id=limitless&environment=dev&selected_thread_id={beta_thread.id}",
        headers=alpha_headers,
    )

    assert alpha_response.status_code == 200
    alpha_body = alpha_response.json()
    assert alpha_body["summary"] == {
        "thread_count": 1,
        "unread_count": 1,
        "approval_required_count": 0,
    }
    assert [thread["thread_id"] for thread in alpha_body["threads"]] == [alpha_thread.id]
    assert alpha_body["selected_thread_id"] == alpha_thread.id
    assert hidden_response.status_code == 404
    assert hidden_response.json()["detail"] == "Mission Control thread not found"


def test_tasks_endpoint_hides_other_org_threads_with_same_scope(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    base_time = datetime(2026, 4, 18, 15, 0, tzinfo=UTC)

    alpha_thread = mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=1,
            contact=MissionControlContactRecord(display_name="Alpha Follow Up", phone="+155****0707"),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Can you call me after lunch?",
                    created_at=base_time,
                )
            ],
            context={
                "org_id": "org_alpha",
                "manual_call_due_at": (base_time + timedelta(minutes=30)).isoformat(),
                "reply_needs_review": True,
                "booking_status": "pending",
                "sequence_status": "active",
            },
            created_at=base_time,
            updated_at=base_time,
        )
    )
    mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=1,
            contact=MissionControlContactRecord(display_name="Beta Follow Up", phone="+155****0808"),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Beta org task",
                    created_at=base_time,
                )
            ],
            context={
                "org_id": "org_beta",
                "manual_call_due_at": (base_time + timedelta(minutes=35)).isoformat(),
                "reply_needs_review": True,
                "booking_status": "pending",
                "sequence_status": "active",
            },
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=1),
        )
    )

    response = client.get(
        "/mission-control/tasks?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["due_count"] == 1
    assert [task["thread_id"] for task in body["tasks"]] == [alpha_thread.id]


def test_mission_control_task_action_endpoints_mutate_state(client) -> None:
    reset_control_plane_state()
    base_time = datetime(2026, 4, 17, 16, 0, tzinfo=UTC)

    campaign = mission_control_service.campaigns_repository.upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Call Back Wave",
            status=CampaignStatus.ACTIVE,
            created_at=base_time,
            updated_at=base_time,
        )
    )
    lead = mission_control_service.leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.ACTIVE,
            campaign_id=campaign.id,
            external_key="thread-lead-001",
            email="operator@example.com",
            phone="+15550001111",
            first_name="Operator",
            last_name="Lead",
            created_at=base_time,
            updated_at=base_time,
        )
    )
    mission_control_service.campaign_memberships_repository.upsert(
        CampaignMembershipRecord(
            business_id="limitless",
            environment="dev",
            lead_id=lead.id,
            campaign_id=campaign.id,
            status=CampaignMembershipStatus.ACTIVE,
            subscribed_at=base_time,
        )
    )
    task = mission_control_service.tasks_repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            lead_id=lead.id,
            title="Call operator lead",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_CALL,
            priority=TaskPriority.HIGH,
            due_at=base_time + timedelta(minutes=15),
            idempotency_key="task-operator-lead",
            details={"source": "mission_control"},
            created_at=base_time,
        )
    )
    thread = mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=1,
            contact=MissionControlContactRecord(display_name="Operator Lead", phone=lead.phone, email=lead.email),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Please call me back.",
                    created_at=base_time + timedelta(minutes=1),
                )
            ],
            context={
                "lead_id": lead.id,
                "manual_call_due_at": (base_time + timedelta(minutes=10)).isoformat(),
                "reply_needs_review": True,
                "sequence_status": "active",
                "booking_status": "pending",
            },
            created_at=base_time,
            updated_at=base_time,
        )
    )

    complete_response = client.post(
        f"/mission-control/tasks/{thread.id}/complete",
        json={"notes": "Called and left a voicemail.", "follow_up_outcome": "left_voicemail"},
        headers=AUTH_HEADERS,
    )
    assert complete_response.status_code == 200
    complete_body = complete_response.json()
    assert complete_body["status"] == "completed"
    assert complete_body["completed_task_count"] == 1
    assert mission_control_service.tasks_repository.get(task.id).status == TaskStatus.COMPLETED

    review_task = mission_control_service.tasks_repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            lead_id=lead.id,
            title="Review reply after callback",
            status=TaskStatus.OPEN,
            task_type=TaskType.SUPPRESSION_REVIEW,
            priority=TaskPriority.NORMAL,
            idempotency_key="task-review-follow-up",
            details={"source": "review_queue"},
            created_at=base_time + timedelta(minutes=1),
        )
    )

    suppress_response = client.post(
        f"/mission-control/leads/{thread.id}/suppress",
        json={"reason": "do_not_contact", "note": "owner requested"},
        headers=AUTH_HEADERS,
    )
    assert suppress_response.status_code == 200
    suppress_body = suppress_response.json()
    assert suppress_body["action"] == "suppressed"
    assert suppress_body["lead_status"] == "suppressed"
    assert mission_control_service.leads_repository.get(lead.id).lifecycle_status == LeadLifecycleStatus.SUPPRESSED
    assert mission_control_service.campaign_memberships_repository.list_for_lead(lead.id)[0].status == CampaignMembershipStatus.SUPPRESSED
    assert mission_control_service.tasks_repository.get(task.id).status == TaskStatus.COMPLETED
    assert mission_control_service.tasks_repository.get(review_task.id).status == TaskStatus.CANCELLED

    unsuppress_response = client.post(
        f"/mission-control/leads/{thread.id}/unsuppress",
        json={"note": "reinstated"},
        headers=AUTH_HEADERS,
    )
    assert unsuppress_response.status_code == 200
    unsuppress_body = unsuppress_response.json()
    assert unsuppress_body["action"] == "unsuppressed"
    assert unsuppress_body["lead_status"] == "active"
    assert mission_control_service.leads_repository.get(lead.id).lifecycle_status == LeadLifecycleStatus.ACTIVE
    assert mission_control_service.campaign_memberships_repository.list_for_lead(lead.id)[0].status == CampaignMembershipStatus.ACTIVE


def test_mission_control_task_actions_fail_closed_for_tenant_actor_when_target_lane_is_not_org_scoped(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    base_time = datetime(2026, 4, 18, 16, 0, tzinfo=UTC)

    campaign = mission_control_service.campaigns_repository.upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Beta Lead Queue",
            status=CampaignStatus.ACTIVE,
            created_at=base_time,
            updated_at=base_time,
        )
    )
    beta_lead = mission_control_service.leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.ACTIVE,
            campaign_id=campaign.id,
            external_key="beta-shared-thread-lead",
            email="beta-thread@example.com",
            phone="+155****1212",
            first_name="Beta",
            last_name="Lead",
            created_at=base_time,
            updated_at=base_time,
        )
    )
    beta_membership = mission_control_service.campaign_memberships_repository.upsert(
        CampaignMembershipRecord(
            business_id="limitless",
            environment="dev",
            lead_id=beta_lead.id,
            campaign_id=campaign.id,
            status=CampaignMembershipStatus.ACTIVE,
            subscribed_at=base_time,
        )
    )
    beta_task = mission_control_service.tasks_repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            lead_id=beta_lead.id,
            title="Call beta lead",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_CALL,
            priority=TaskPriority.HIGH,
            due_at=base_time + timedelta(minutes=15),
            idempotency_key="task-beta-cross-org",
            created_at=base_time,
        )
    )
    alpha_thread = mission_control_service.upsert_thread_projection(
        MissionControlThreadRecord(
            business_id="limitless",
            environment="dev",
            channel="sms",
            status="open",
            unread_count=1,
            contact=MissionControlContactRecord(
                display_name="Alpha Thread Foreign Lead",
                phone=beta_lead.phone,
                email=beta_lead.email,
            ),
            messages=[
                MissionControlMessageRecord(
                    direction="inbound",
                    channel="sms",
                    body="Cross-org mutation probe",
                    created_at=base_time,
                )
            ],
            context={
                "org_id": "org_alpha",
                "lead_id": beta_lead.id,
                "manual_call_due_at": (base_time + timedelta(minutes=10)).isoformat(),
                "reply_needs_review": True,
                "sequence_status": "active",
                "booking_status": "pending",
            },
            created_at=base_time,
            updated_at=base_time,
        )
    )

    complete_response = client.post(
        f"/mission-control/tasks/{alpha_thread.id}/complete",
        json={"notes": "Should be denied", "follow_up_outcome": "left_voicemail"},
        headers=alpha_headers,
    )
    suppress_response = client.post(
        f"/mission-control/leads/{alpha_thread.id}/suppress",
        json={"reason": "do_not_contact", "note": "should not land"},
        headers=alpha_headers,
    )

    assert complete_response.status_code == 404
    assert suppress_response.status_code == 404
    assert mission_control_service.tasks_repository.get(beta_task.id).status == TaskStatus.OPEN
    assert mission_control_service.leads_repository.get(beta_lead.id).lifecycle_status == LeadLifecycleStatus.ACTIVE
    assert mission_control_service.campaign_memberships_repository.get(beta_membership.id).status == CampaignMembershipStatus.ACTIVE

    mission_control_service.leads_repository.upsert(
        beta_lead.model_copy(
            update={
                "lifecycle_status": LeadLifecycleStatus.SUPPRESSED,
                "updated_at": base_time + timedelta(minutes=1),
            }
        )
    )
    mission_control_service.campaign_memberships_repository.upsert(
        beta_membership.model_copy(
            update={
                "status": CampaignMembershipStatus.SUPPRESSED,
                "unsubscribed_at": base_time + timedelta(minutes=1),
            }
        )
    )

    unsuppress_response = client.post(
        f"/mission-control/leads/{alpha_thread.id}/unsuppress",
        json={"note": "should stay suppressed"},
        headers=alpha_headers,
    )

    assert unsuppress_response.status_code == 404
    assert mission_control_service.leads_repository.get(beta_lead.id).lifecycle_status == LeadLifecycleStatus.SUPPRESSED
    assert mission_control_service.campaign_memberships_repository.get(beta_membership.id).status == CampaignMembershipStatus.SUPPRESSED


def test_agents_endpoint_projects_release_event_without_false_rollback_source(client) -> None:
    reset_control_plane_state()
    agent_id, revision_id = create_published_agent(
        client,
        headers=AUTH_HEADERS,
        name="Mission Control Publish Agent",
        release_channel="dogfood",
    )

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/clone",
        headers=AUTH_HEADERS,
    )
    assert clone_response.status_code == 200
    second_revision_id = clone_response.json()["revisions"][-1]["id"]

    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{second_revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200

    response = client.get(
        "/mission-control/agents?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    agents_by_id = {agent["id"]: agent for agent in response.json()["agents"]}
    assert agents_by_id[agent_id]["release"]["event_type"] == "publish"
    assert agents_by_id[agent_id]["release"]["rollback_source_revision_id"] is None


def test_agents_endpoint_omits_stale_release_posture_when_active_revision_moves_without_event(client) -> None:
    reset_control_plane_state()
    agent_id, revision_id = create_published_agent(
        client,
        headers=AUTH_HEADERS,
        name="Mission Control Diverged Release Agent",
        release_channel="dogfood",
    )

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/clone",
        headers=AUTH_HEADERS,
    )
    assert clone_response.status_code == 200
    newer_revision_id = clone_response.json()["revisions"][-1]["id"]

    registry_response = mission_control_service.agent_registry_service.publish_revision(agent_id, newer_revision_id)
    assert registry_response is not None

    response = client.get(
        "/mission-control/agents?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    agents_by_id = {agent["id"]: agent for agent in response.json()["agents"]}
    assert agents_by_id[agent_id]["active_revision_id"] == newer_revision_id
    assert agents_by_id[agent_id]["release"] is None


def test_agents_endpoint_does_not_fabricate_host_adapter_without_active_revision(client) -> None:
    reset_control_plane_state()

    created = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Draft Only Agent",
            "config": {"prompt": "draft prompt"},
        },
        headers=AUTH_HEADERS,
    )
    assert created.status_code == 200
    agent_id = created.json()["agent"]["id"]

    response = client.get(
        "/mission-control/agents?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    agents_by_id = {agent["id"]: agent for agent in response.json()["agents"]}
    assert agents_by_id[agent_id]["active_revision_id"] is None
    assert agents_by_id[agent_id]["host_adapter"] is None


def test_runs_endpoint_returns_replay_release_state(client) -> None:
    reset_control_plane_state()

    agent_id, revision_id = create_published_agent(
        client,
        headers=AUTH_HEADERS,
        name="Replay Read Model Agent",
        release_channel="dogfood",
    )

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-runs-parent",
            "payload": {"topic": "atlanta probate leads"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )
    parent_run_id = command_response.json()["run_id"]

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/clone",
        headers=AUTH_HEADERS,
    )
    assert clone_response.status_code == 200
    second_revision_id = clone_response.json()["revisions"][-1]["id"]

    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{second_revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200

    rollback_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{revision_id}/rollback",
        json={"notes": "return to known-good baseline"},
        headers=AUTH_HEADERS,
    )
    assert rollback_response.status_code == 200
    rollback_active_revision_id = rollback_response.json()["agent"]["active_revision_id"]

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
    parent_replay = runs_by_id[parent_run_id]["replay"]
    assert parent_replay["role"] == "parent"
    assert parent_replay["requested_at"]
    assert parent_replay["resolved_at"]
    assert parent_replay["replay_reason"] == "refresh market snapshot"
    assert parent_replay["requires_approval"] is False
    assert parent_replay["approval_id"] is None
    assert parent_replay["child_run_id"] == child_run_id
    assert parent_replay["parent_run_id"] is None
    assert parent_replay["triggering_actor"] == {
        "org_id": "org_internal",
        "actor_id": get_settings().default_actor_id,
        "actor_type": get_settings().default_actor_type,
    }
    assert parent_replay["source"] == {
        "agent_id": agent_id,
        "agent_revision_id": revision_id,
        "active_revision_id": revision_id,
        "revision_state": "deprecated",
        "release_channel": "dogfood",
        "release_event_id": parent_replay["source"]["release_event_id"],
        "release_event_type": "publish",
    }
    assert parent_replay["replay"]["agent_id"] == agent_id
    assert parent_replay["replay"]["agent_revision_id"] == revision_id
    assert parent_replay["replay"]["active_revision_id"] == rollback_active_revision_id
    assert parent_replay["replay"]["revision_state"] in {"published", "deprecated"}
    assert parent_replay["replay"]["release_channel"] == "dogfood"
    assert parent_replay["replay"]["release_event_id"]
    assert parent_replay["replay"]["release_event_type"] == "rollback"
    assert parent_replay["source"]["release_event_id"] != parent_replay["replay"]["release_event_id"]

    child_replay = runs_by_id[child_run_id]["replay"]
    assert child_replay["role"] == "child"
    assert child_replay["requested_at"]
    assert child_replay["resolved_at"]
    assert child_replay["replay_reason"] == "refresh market snapshot"
    assert child_replay["requires_approval"] is None
    assert child_replay["approval_id"] is None
    assert child_replay["child_run_id"] == child_run_id
    assert child_replay["parent_run_id"] == parent_run_id
    assert child_replay["triggering_actor"] == {
        "org_id": "org_internal",
        "actor_id": get_settings().default_actor_id,
        "actor_type": get_settings().default_actor_type,
    }
    assert child_replay["source"] == {
        "agent_id": agent_id,
        "agent_revision_id": revision_id,
        "active_revision_id": revision_id,
        "revision_state": "deprecated",
        "release_channel": "dogfood",
        "release_event_id": child_replay["source"]["release_event_id"],
        "release_event_type": "publish",
    }
    assert child_replay["replay"]["agent_id"] == agent_id
    assert child_replay["replay"]["agent_revision_id"] == revision_id
    assert child_replay["replay"]["active_revision_id"] == rollback_active_revision_id
    assert child_replay["replay"]["revision_state"] in {"published", "deprecated"}
    assert child_replay["replay"]["release_channel"] == "dogfood"
    assert child_replay["replay"]["release_event_id"]
    assert child_replay["replay"]["release_event_type"] == "rollback"


def test_runs_endpoint_projects_parent_replay_as_resolved_after_approval(client) -> None:
    reset_control_plane_state()

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-runs-approval-parent",
            "payload": {"campaign_id": "camp_runs_parent"},
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    approval_id = command_response.json()["approval_id"]

    approval_response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor_id": "ops-1"},
        headers=AUTH_HEADERS,
    )
    assert approval_response.status_code == 200
    parent_run_id = approval_response.json()["run_id"]

    replay_response = client.post(
        f"/replays/{parent_run_id}",
        json={"reason": "rerun delivery"},
        headers=AUTH_HEADERS,
    )
    assert replay_response.status_code == 409
    replay_approval_id = replay_response.json()["approval_id"]

    approved_replay_response = client.post(
        f"/approvals/{replay_approval_id}/approve",
        json={"actor_id": "ops-approver"},
        headers=AUTH_HEADERS,
    )
    assert approved_replay_response.status_code == 200
    child_run_id = approved_replay_response.json()["run_id"]

    response = client.get(
        "/mission-control/runs?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    runs_by_id = {run["id"]: run for run in response.json()["runs"]}
    parent_replay = runs_by_id[parent_run_id]["replay"]
    assert parent_replay["role"] == "parent"
    assert parent_replay["requires_approval"] is False
    assert parent_replay["approval_id"] == replay_approval_id
    assert parent_replay["child_run_id"] == child_run_id
    assert parent_replay["resolved_at"]


def test_runs_endpoint_hides_other_org_runs_with_same_scope(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")

    alpha_run = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-runs-alpha-org",
            "payload": {"topic": "alpha probate", "org_id": "org_alpha"},
        },
        headers=AUTH_HEADERS,
    )
    beta_run = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-runs-beta-org",
            "payload": {"topic": "beta probate", "org_id": "org_beta"},
        },
        headers=AUTH_HEADERS,
    )

    assert alpha_run.status_code == 201
    assert beta_run.status_code == 201

    response = client.get(
        "/mission-control/runs?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )

    assert response.status_code == 200
    assert [run["id"] for run in response.json()["runs"]] == [alpha_run.json()["run_id"]]


def test_approvals_and_assets_endpoints_hide_other_org_records_with_same_scope(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    alpha_agent_id, _ = create_published_agent(client, headers=alpha_headers, name="Alpha Asset Agent")
    beta_agent_id, _ = create_published_agent(client, headers=beta_headers, name="Beta Asset Agent")

    alpha_asset = client.post(
        "/agent-assets",
        json={
            "agent_id": alpha_agent_id,
            "asset_type": "calendar",
            "label": "Alpha Calendar",
            "metadata": {"provider": "cal.com"},
        },
        headers=AUTH_HEADERS,
    )
    beta_asset = client.post(
        "/agent-assets",
        json={
            "agent_id": beta_agent_id,
            "asset_type": "calendar",
            "label": "Beta Calendar",
            "metadata": {"provider": "cal.com"},
        },
        headers=AUTH_HEADERS,
    )
    assert alpha_asset.status_code == 200
    assert beta_asset.status_code == 200

    alpha_approval = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-approvals-alpha-org",
            "payload": {"campaign_id": "camp_alpha_assets", "org_id": "org_alpha"},
        },
        headers=AUTH_HEADERS,
    )
    beta_approval = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-approvals-beta-org",
            "payload": {"campaign_id": "camp_beta_assets", "org_id": "org_beta"},
        },
        headers=AUTH_HEADERS,
    )
    assert alpha_approval.status_code == 201
    assert beta_approval.status_code == 201

    approvals_response = client.get(
        "/mission-control/approvals?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )
    assets_response = client.get(
        "/mission-control/settings/assets?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )

    assert approvals_response.status_code == 200
    assert [approval["id"] for approval in approvals_response.json()["approvals"]] == [
        alpha_approval.json()["approval_id"]
    ]
    assert assets_response.status_code == 200
    assert [asset["agent_id"] for asset in assets_response.json()["assets"]] == [alpha_agent_id]


def test_autonomy_visibility_hides_other_org_runs_and_unscoped_lead_quality(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")

    alpha_run = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "mc-autonomy-alpha-org",
            "payload": {"topic": "alpha autonomy", "org_id": "org_alpha"},
        },
        headers=AUTH_HEADERS,
    )
    beta_approval = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-autonomy-beta-approval",
            "payload": {"campaign_id": "camp_beta_visibility", "org_id": "org_beta"},
        },
        headers=AUTH_HEADERS,
    )
    assert alpha_run.status_code == 201
    assert beta_approval.status_code == 201

    mission_control_service.leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.ACTIVE,
            external_key="unscoped-alpha-visibility-lead",
            email="visibility@example.com",
        )
    )

    response = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["active_run"]["id"] == alpha_run.json()["run_id"]
    assert body["pending_approval_count"] == 0
    assert body["lead_quality"] == 0.0
    assert body["confidence"] == 0.0
    assert body["next_action"] == "continue_run:run_market_research"


def test_lead_machine_and_provider_extras_fail_closed_for_tenant_orgs(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    base_time = datetime(2026, 4, 18, 17, 0, tzinfo=UTC)

    campaign = mission_control_service.campaigns_repository.upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Instantly Tenant Leak Probe",
            provider_name="instantly",
            provider_campaign_id="inst_tenant_probe",
            status=CampaignStatus.ACTIVE,
            created_at=base_time,
            updated_at=base_time,
        )
    )
    mission_control_service.leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.INSTANTLY_IMPORT,
            lifecycle_status=LeadLifecycleStatus.ACTIVE,
            campaign_id=campaign.id,
            provider_name="instantly",
            provider_lead_id="inst_lead_probe",
            external_key="tenant-leak-probe",
            email="instantly-probe@example.com",
            created_at=base_time,
            updated_at=base_time,
        )
    )

    lead_machine_response = client.get(
        "/mission-control/lead-machine?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )
    provider_extras_response = client.get(
        "/mission-control/providers/instantly/extras?business_id=limitless&environment=dev",
        headers=alpha_headers,
    )

    assert lead_machine_response.status_code == 200
    assert provider_extras_response.status_code == 200
    lead_machine_body = lead_machine_response.json()
    provider_extras_body = provider_extras_response.json()
    assert lead_machine_body["queue"] == {
        "total_lead_count": 0,
        "ready_count": 0,
        "active_count": 0,
        "suppressed_count": 0,
        "interested_count": 0,
    }
    assert lead_machine_body["campaigns"]["total_campaign_count"] == 0
    assert lead_machine_body["tasks"]["open_count"] == 0
    assert provider_extras_body["configured"] is False
    assert provider_extras_body["summary"]["campaign_count"] == 0
    assert provider_extras_body["summary"]["lead_count"] == 0
    assert provider_extras_body["labels"]["notes"] == [
        "Tenant-scoped provider extras projection is not available yet for non-internal orgs."
    ]


def test_secret_audit_and_usage_endpoints_scope_to_actor_org(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    alpha_agent_id, alpha_revision_id = create_published_agent(
        client,
        headers=alpha_headers,
        name="Alpha Secret Agent",
        compatibility_metadata={"requires_secrets": ["alpha_token"]},
    )
    _, beta_revision_id = create_published_agent(
        client,
        headers=beta_headers,
        name="Beta Secret Agent",
        compatibility_metadata={"requires_secrets": ["beta_token"]},
    )

    alpha_secret = client.post(
        "/secrets",
        json={"org_id": "org_alpha", "name": "alpha_token", "secret_value": "***"},
        headers=AUTH_HEADERS,
    )
    beta_secret = client.post(
        "/secrets",
        json={"org_id": "org_beta", "name": "beta_token", "secret_value": "***"},
        headers=AUTH_HEADERS,
    )
    assert alpha_secret.status_code == 200
    assert beta_secret.status_code == 200

    alpha_binding = client.post(
        f"/secrets/{alpha_secret.json()['id']}/bindings",
        json={"agent_revision_id": alpha_revision_id, "binding_name": "alpha_token"},
        headers=AUTH_HEADERS,
    )
    beta_binding = client.post(
        f"/secrets/{beta_secret.json()['id']}/bindings",
        json={"agent_revision_id": beta_revision_id, "binding_name": "beta_token"},
        headers=AUTH_HEADERS,
    )
    assert alpha_binding.status_code == 200
    assert beta_binding.status_code == 200

    alpha_audit = client.post(
        "/audit",
        json={
            "event_type": "secret_accessed",
            "summary": "Alpha secret accessed",
            "org_id": "org_alpha",
            "resource_type": "secret",
            "resource_id": alpha_secret.json()["id"],
            "agent_id": alpha_agent_id,
            "agent_revision_id": alpha_revision_id,
        },
        headers=alpha_headers,
    )
    beta_audit = client.post(
        "/audit",
        json={
            "event_type": "secret_accessed",
            "summary": "Beta secret accessed",
            "org_id": "org_beta",
            "resource_type": "secret",
            "resource_id": beta_secret.json()["id"],
            "agent_revision_id": beta_revision_id,
        },
        headers=beta_headers,
    )
    alpha_usage = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "org_id": "org_alpha",
            "agent_id": alpha_agent_id,
            "agent_revision_id": alpha_revision_id,
            "count": 3,
        },
        headers=alpha_headers,
    )
    beta_usage = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "org_id": "org_beta",
            "agent_revision_id": beta_revision_id,
            "count": 7,
        },
        headers=beta_headers,
    )
    assert alpha_audit.status_code == 200
    assert beta_audit.status_code == 200
    assert alpha_usage.status_code == 200
    assert beta_usage.status_code == 200

    secrets_response = client.get("/mission-control/settings/secrets", headers=alpha_headers)
    alpha_bindings_response = client.get(
        f"/mission-control/settings/secrets/bindings/{alpha_revision_id}",
        headers=alpha_headers,
    )
    foreign_bindings_response = client.get(
        f"/mission-control/settings/secrets/bindings/{beta_revision_id}",
        headers=alpha_headers,
    )
    audit_response = client.get("/mission-control/audit", headers=alpha_headers)
    usage_response = client.get("/mission-control/usage", headers=alpha_headers)
    mismatched_secrets = client.get("/mission-control/settings/secrets?org_id=org_beta", headers=alpha_headers)
    mismatched_audit = client.get("/mission-control/audit?org_id=org_beta", headers=alpha_headers)
    mismatched_usage = client.get("/mission-control/usage?org_id=org_beta", headers=alpha_headers)

    assert secrets_response.status_code == 200
    assert [secret["org_id"] for secret in secrets_response.json()["secrets"]] == ["org_alpha"]
    assert alpha_bindings_response.status_code == 200
    assert [binding["org_id"] for binding in alpha_bindings_response.json()["bindings"]] == ["org_alpha"]
    assert foreign_bindings_response.status_code == 404
    assert audit_response.status_code == 200
    assert all(event["org_id"] == "org_alpha" for event in audit_response.json()["events"])
    assert any(event["event_type"] == "secret_accessed" for event in audit_response.json()["events"])
    assert usage_response.status_code == 200
    assert usage_response.json()["summary"]["total_count"] == 3
    assert [event["org_id"] for event in usage_response.json()["events"]] == ["org_alpha"]
    assert mismatched_secrets.status_code == 422
    assert mismatched_audit.status_code == 422
    assert mismatched_usage.status_code == 422


def test_governance_endpoint_bundles_org_scoped_governance_without_secret_read_noise(client) -> None:
    reset_control_plane_state()
    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    alpha_agent_id, alpha_revision_id = create_published_agent(
        client,
        headers=alpha_headers,
        name="Alpha Governance Healthy Agent",
        compatibility_metadata={"requires_secrets": ["alpha_token"]},
    )
    _, missing_revision_id = create_published_agent(
        client,
        headers=alpha_headers,
        name="Alpha Governance Missing Agent",
        compatibility_metadata={"requires_secrets": ["alpha_missing"]},
    )
    _, beta_revision_id = create_published_agent(
        client,
        headers=beta_headers,
        name="Beta Governance Agent",
        compatibility_metadata={"requires_secrets": ["beta_token"]},
    )
    draft_agent = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Alpha Draft Governance Agent",
            "config": {"prompt": "draft governance prompt"},
            "compatibility_metadata": {"requires_secrets": ["draft_only_secret"]},
        },
        headers=alpha_headers,
    )
    assert draft_agent.status_code == 200

    alpha_secret = client.post(
        "/secrets",
        json={"org_id": "org_alpha", "name": "alpha_token", "secret_value": "***"},
        headers=AUTH_HEADERS,
    )
    beta_secret = client.post(
        "/secrets",
        json={"org_id": "org_beta", "name": "beta_token", "secret_value": "***"},
        headers=AUTH_HEADERS,
    )
    assert alpha_secret.status_code == 200
    assert beta_secret.status_code == 200

    alpha_binding = client.post(
        f"/secrets/{alpha_secret.json()['id']}/bindings",
        json={"agent_revision_id": alpha_revision_id, "binding_name": "alpha_token"},
        headers=AUTH_HEADERS,
    )
    beta_binding = client.post(
        f"/secrets/{beta_secret.json()['id']}/bindings",
        json={"agent_revision_id": beta_revision_id, "binding_name": "beta_token"},
        headers=AUTH_HEADERS,
    )
    assert alpha_binding.status_code == 200
    assert beta_binding.status_code == 200

    alpha_approval = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-governance-alpha-approval",
            "payload": {"campaign_id": "camp_governance_alpha", "org_id": "org_alpha"},
        },
        headers=AUTH_HEADERS,
    )
    beta_approval = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "mc-governance-beta-approval",
            "payload": {"campaign_id": "camp_governance_beta", "org_id": "org_beta"},
        },
        headers=AUTH_HEADERS,
    )
    assert alpha_approval.status_code == 201
    assert beta_approval.status_code == 201

    alpha_audit = client.post(
        "/audit",
        json={
            "event_type": "secret_accessed",
            "summary": "Alpha governance secret accessed",
            "org_id": "org_alpha",
            "resource_type": "secret",
            "resource_id": alpha_secret.json()["id"],
            "agent_id": alpha_agent_id,
            "agent_revision_id": alpha_revision_id,
        },
        headers=alpha_headers,
    )
    beta_audit = client.post(
        "/audit",
        json={
            "event_type": "secret_accessed",
            "summary": "Beta governance secret accessed",
            "org_id": "org_beta",
            "resource_type": "secret",
            "resource_id": beta_secret.json()["id"],
            "agent_revision_id": beta_revision_id,
        },
        headers=beta_headers,
    )
    alpha_usage = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "org_id": "org_alpha",
            "agent_id": alpha_agent_id,
            "agent_revision_id": alpha_revision_id,
            "count": 3,
        },
        headers=alpha_headers,
    )
    beta_usage = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "org_id": "org_beta",
            "agent_revision_id": beta_revision_id,
            "count": 7,
        },
        headers=beta_headers,
    )
    assert alpha_audit.status_code == 200
    assert beta_audit.status_code == 200
    assert alpha_usage.status_code == 200
    assert beta_usage.status_code == 200

    response = client.get("/mission-control/settings/governance", headers=alpha_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["org_id"] == "org_alpha"
    assert [approval["id"] for approval in body["pending_approvals"]] == [alpha_approval.json()["approval_id"]]
    assert body["secrets_health"] == {
        "active_revision_count": 2,
        "healthy_revision_count": 1,
        "attention_revision_count": 1,
        "required_secret_count": 2,
        "configured_secret_count": 1,
        "missing_secret_count": 1,
        "revisions": [
            {
                "agent_id": alpha_agent_id,
                "agent_name": "Alpha Governance Healthy Agent",
                "agent_revision_id": alpha_revision_id,
                "business_id": "limitless",
                "environment": "dev",
                "status": "healthy",
                "required_secret_count": 1,
                "configured_secret_count": 1,
                "missing_secret_count": 0,
                "required_secrets": ["alpha_token"],
                "configured_secrets": ["alpha_token"],
                "missing_secrets": [],
            },
            {
                "agent_id": body["secrets_health"]["revisions"][1]["agent_id"],
                "agent_name": "Alpha Governance Missing Agent",
                "agent_revision_id": missing_revision_id,
                "business_id": "limitless",
                "environment": "dev",
                "status": "attention",
                "required_secret_count": 1,
                "configured_secret_count": 0,
                "missing_secret_count": 1,
                "required_secrets": ["alpha_missing"],
                "configured_secrets": [],
                "missing_secrets": ["alpha_missing"],
            },
        ],
    }
    assert all(event["org_id"] == "org_alpha" for event in body["recent_audit"])
    assert any(event["summary"] == "Alpha governance secret accessed" for event in body["recent_audit"])
    assert body["usage_summary"]["total_count"] == 3
    assert body["usage_summary"]["by_kind"] == {"tool_call": 3}
    assert [event["org_id"] for event in body["recent_usage"]] == ["org_alpha"]
    assert [event["count"] for event in body["recent_usage"]] == [3]

    secret_accessed_events = client.get(
        "/mission-control/audit?event_type=secret_accessed",
        headers=alpha_headers,
    )
    assert secret_accessed_events.status_code == 200
    assert [event["summary"] for event in secret_accessed_events.json()["events"]] == [
        "Alpha governance secret accessed"
    ]


def test_provider_status_endpoint_reflects_configured_sms_and_email(client, monkeypatch) -> None:
    reset_control_plane_state()
    monkeypatch.setenv("TEXTGRID_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TEXTGRID_AUTH_TOKEN", "token123")
    monkeypatch.setenv("TEXTGRID_FROM_NUMBER", "+13475550123")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "Relay <relay@send.limitleshome.com>")
    get_settings.cache_clear()

    response = client.get("/mission-control/providers/status", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["sms"]["provider"] == "textgrid"
    assert body["sms"]["configured"] is True
    assert body["sms"]["can_send"] is True
    assert body["sms"]["sender_identity"] == "+13475550123"
    assert body["email"]["provider"] == "resend"
    assert body["email"]["configured"] is True
    assert body["email"]["can_send"] is True
    assert body["email"]["sender_identity"] == "Relay <relay@send.limitleshome.com>"


def test_sms_test_endpoint_returns_provider_acceptance(client, monkeypatch) -> None:
    reset_control_plane_state()
    captured = {}

    def fake_send(settings, *, to: str, body: str):
        captured["to"] = to
        captured["body"] = body
        captured["settings"] = settings
        return {
            "channel": "sms",
            "provider": "textgrid",
            "status": "queued",
            "provider_message_id": "SM123",
            "to": to,
            "from_identity": "+13475550123",
            "attempted_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            "error_message": None,
        }

    monkeypatch.setattr("app.services.mission_control_service.send_test_sms", fake_send)

    response = client.post(
        "/mission-control/outbound/sms/test",
        json={"to": "+13475550123", "body": "hello human"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["channel"] == "sms"
    assert body["provider"] == "textgrid"
    assert body["status"] == "queued"
    assert body["provider_message_id"] == "SM123"
    assert body["to"] == "+13475550123"
    assert captured["to"] == "+13475550123"
    assert captured["body"] == "hello human"


def test_email_test_endpoint_returns_provider_acceptance(client, monkeypatch) -> None:
    reset_control_plane_state()
    captured = {}

    def fake_send(settings, *, to: str, subject: str, text: str, html: str | None = None):
        captured["to"] = to
        captured["subject"] = subject
        captured["text"] = text
        captured["html"] = html
        return {
            "channel": "email",
            "provider": "resend",
            "status": "queued",
            "provider_message_id": "em_123",
            "to": to,
            "from_identity": "Relay <relay@send.limitleshome.com>",
            "attempted_at": datetime(2026, 4, 14, 12, 1, tzinfo=UTC),
            "error_message": None,
        }

    monkeypatch.setattr("app.services.mission_control_service.send_test_email", fake_send)

    response = client.post(
        "/mission-control/outbound/email/test",
        json={"to": "martinhomeoffers@gmail.com", "subject": "Mission Control smoke test", "text": "hello human"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["channel"] == "email"
    assert body["provider"] == "resend"
    assert body["status"] == "queued"
    assert body["provider_message_id"] == "em_123"
    assert body["to"] == "martinhomeoffers@gmail.com"
    assert captured["subject"] == "Mission Control smoke test"
    assert captured["text"] == "hello human"


def test_sms_test_endpoint_maps_provider_errors_to_502(client, monkeypatch) -> None:
    reset_control_plane_state()

    def fake_send(settings, *, to: str, body: str):
        raise RuntimeError("SMS Sending Limit reached. Please contact support")

    monkeypatch.setattr("app.services.mission_control_service.send_test_sms", fake_send)

    response = client.post(
        "/mission-control/outbound/sms/test",
        json={"to": "+13475550123", "body": "hello human"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "SMS Sending Limit reached. Please contact support"
