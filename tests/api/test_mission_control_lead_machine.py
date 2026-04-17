from datetime import UTC, datetime, timedelta

from app.db.automation_runs import AutomationRunsRepository
from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import get_control_plane_client
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.tasks import TasksRepository
from app.models.automation_runs import AutomationRunRecord, AutomationRunStatus
from app.models.campaigns import CampaignMembershipRecord, CampaignMembershipStatus, CampaignRecord, CampaignStatus
from app.models.lead_events import LeadEventRecord
from app.models.leads import LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_lead_machine_endpoint_returns_probate_outbound_summary(client) -> None:
    reset_control_plane_state()
    control_plane_client = get_control_plane_client()
    leads_repository = LeadsRepository(control_plane_client)
    campaigns_repository = CampaignsRepository(control_plane_client)
    memberships_repository = CampaignMembershipsRepository(control_plane_client)
    lead_events_repository = LeadEventsRepository(control_plane_client)
    automation_runs_repository = AutomationRunsRepository(control_plane_client)
    tasks_repository = TasksRepository(control_plane_client)
    base_time = datetime(2026, 4, 16, 19, 0, tzinfo=UTC)

    campaign = campaigns_repository.upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Probate Wave 2",
            provider_name="instantly",
            provider_campaign_id="inst_002",
            status=CampaignStatus.ACTIVE,
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=1),
        )
    )
    lead = leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.ACTIVE,
            campaign_id=campaign.id,
            external_key="probate-api-lead",
            email="api@example.com",
            first_name="Api",
            last_name="Lead",
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=2),
        )
    )
    memberships_repository.upsert(
        CampaignMembershipRecord(
            business_id="limitless",
            environment="dev",
            lead_id=lead.id,
            campaign_id=campaign.id,
            status=CampaignMembershipStatus.ACTIVE,
            subscribed_at=base_time + timedelta(minutes=3),
        )
    )
    lead_events_repository.append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id=lead.id,
            campaign_id=campaign.id,
            provider_name="instantly",
            event_type="lead.email.sent",
            event_timestamp=base_time + timedelta(minutes=4),
            idempotency_key="api-event-sent",
        )
    )
    automation_runs_repository.create(
        AutomationRunRecord(
            business_id="limitless",
            environment="dev",
            workflow_name="lead_webhook_processing",
            lead_id=lead.id,
            campaign_id=campaign.id,
            status=AutomationRunStatus.COMPLETED,
            idempotency_key="api-run",
            created_at=base_time + timedelta(minutes=5),
            updated_at=base_time + timedelta(minutes=6),
            completed_at=base_time + timedelta(minutes=6),
        )
    )
    tasks_repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            lead_id=lead.id,
            title="Review probate reply",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_REVIEW,
            priority=TaskPriority.HIGH,
            due_at=base_time + timedelta(minutes=7),
            idempotency_key="api-task-review",
            created_at=base_time + timedelta(minutes=6),
        )
    )

    response = client.get(
        "/mission-control/lead-machine?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["queue"] == {
        "total_lead_count": 1,
        "ready_count": 0,
        "active_count": 1,
        "suppressed_count": 0,
        "interested_count": 0,
    }
    assert body["campaigns"]["items"] == [
        {
            "campaign_id": campaign.id,
            "name": "Probate Wave 2",
            "status": "active",
            "member_count": 1,
            "active_member_count": 1,
            "suppressed_member_count": 0,
        }
    ]
    assert body["tasks"]["items"][0]["title"] == "Review probate reply"
    assert [item["kind"] for item in body["timeline"]["items"]] == ["task", "run", "event"]
