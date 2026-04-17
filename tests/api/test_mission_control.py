from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
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
    assert "updated_at" in body


def test_agents_endpoint_filters_to_requested_scope(client) -> None:
    reset_control_plane_state()

    scoped_agent = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Scoped Agent",
            "config": {"prompt": "Stay scoped"},
        },
        headers=AUTH_HEADERS,
    ).json()
    scoped_agent_id = scoped_agent["agent"]["id"]
    scoped_revision_id = scoped_agent["revisions"][0]["id"]
    scoped_publish_response = client.post(
        f"/agents/{scoped_agent_id}/revisions/{scoped_revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert scoped_publish_response.status_code == 200

    other_agent = client.post(
        "/agents",
        json={
            "business_id": "otherco",
            "environment": "prod",
            "name": "Other Agent",
            "config": {"prompt": "Stay out of scope"},
        },
        headers=AUTH_HEADERS,
    ).json()
    other_agent_id = other_agent["agent"]["id"]
    other_revision_id = other_agent["revisions"][0]["id"]
    other_publish_response = client.post(
        f"/agents/{other_agent_id}/revisions/{other_revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert other_publish_response.status_code == 200

    response = client.get(
        "/mission-control/agents?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["agents"]) == 1
    assert body["agents"][0]["id"] == scoped_agent_id


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
