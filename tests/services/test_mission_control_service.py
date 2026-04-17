from datetime import UTC, datetime, timedelta

from app.db.automation_runs import AutomationRunsRepository
from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.tasks import TasksRepository
from app.models.automation_runs import AutomationRunRecord, AutomationRunStatus
from app.models.campaigns import CampaignMembershipRecord, CampaignMembershipStatus, CampaignRecord, CampaignStatus
from app.models.lead_events import LeadEventRecord
from app.models.leads import LeadInterestStatus, LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType
from app.services.mission_control_service import MissionControlService


def test_get_lead_machine_builds_probate_outbound_summary() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    leads_repository = LeadsRepository(client)
    campaigns_repository = CampaignsRepository(client)
    memberships_repository = CampaignMembershipsRepository(client)
    lead_events_repository = LeadEventsRepository(client)
    automation_runs_repository = AutomationRunsRepository(client)
    tasks_repository = TasksRepository(client)
    service = MissionControlService(
        client=client,
        leads_repository=leads_repository,
        campaigns_repository=campaigns_repository,
        campaign_memberships_repository=memberships_repository,
        lead_events_repository=lead_events_repository,
        automation_runs_repository=automation_runs_repository,
        tasks_repository=tasks_repository,
    )
    base_time = datetime(2026, 4, 16, 18, 0, tzinfo=UTC)

    campaign = campaigns_repository.upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Probate Wave 1",
            provider_name="instantly",
            provider_campaign_id="inst_001",
            status=CampaignStatus.ACTIVE,
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=1),
        )
    )
    ready_lead = leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.READY,
            external_key="probate-ready",
            email="ready@example.com",
            first_name="Ready",
            last_name="Lead",
            score=91,
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=2),
        )
    )
    active_lead = leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.ACTIVE,
            campaign_id=campaign.id,
            external_key="probate-active",
            email="active@example.com",
            first_name="Active",
            last_name="Lead",
            lt_interest_status=LeadInterestStatus.INTERESTED,
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=3),
        )
    )
    suppressed_lead = leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.SUPPRESSED,
            campaign_id=campaign.id,
            external_key="probate-suppressed",
            email="suppressed@example.com",
            first_name="Suppressed",
            last_name="Lead",
            created_at=base_time,
            updated_at=base_time + timedelta(minutes=4),
        )
    )
    memberships_repository.upsert(
        CampaignMembershipRecord(
            business_id="limitless",
            environment="dev",
            lead_id=active_lead.id,
            campaign_id=campaign.id,
            status=CampaignMembershipStatus.ACTIVE,
            subscribed_at=base_time + timedelta(minutes=5),
        )
    )
    memberships_repository.upsert(
        CampaignMembershipRecord(
            business_id="limitless",
            environment="dev",
            lead_id=suppressed_lead.id,
            campaign_id=campaign.id,
            status=CampaignMembershipStatus.SUPPRESSED,
            subscribed_at=base_time + timedelta(minutes=6),
        )
    )
    lead_events_repository.append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id=active_lead.id,
            campaign_id=campaign.id,
            provider_name="instantly",
            event_type="lead.email.sent",
            event_timestamp=base_time + timedelta(minutes=7),
            idempotency_key="event-sent",
        )
    )
    lead_events_repository.append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id=active_lead.id,
            campaign_id=campaign.id,
            provider_name="instantly",
            event_type="lead.replied",
            event_timestamp=base_time + timedelta(minutes=9),
            idempotency_key="event-replied",
        )
    )
    automation_runs_repository.create(
        AutomationRunRecord(
            business_id="limitless",
            environment="dev",
            workflow_name="lead_outbound_enrollment",
            lead_id=active_lead.id,
            campaign_id=campaign.id,
            status=AutomationRunStatus.IN_PROGRESS,
            idempotency_key="run-enrollment",
            created_at=base_time + timedelta(minutes=8),
            updated_at=base_time + timedelta(minutes=10),
        )
    )
    tasks_repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            lead_id=active_lead.id,
            title="Call interested probate lead",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_CALL,
            priority=TaskPriority.HIGH,
            due_at=base_time + timedelta(minutes=11),
            idempotency_key="task-call-active",
            created_at=base_time + timedelta(minutes=10),
        )
    )

    response = service.get_lead_machine(business_id="limitless", environment="dev")

    assert response.queue.total_lead_count == 3
    assert response.queue.ready_count == 1
    assert response.queue.active_count == 1
    assert response.queue.suppressed_count == 1
    assert response.queue.interested_count == 1
    assert response.campaigns.total_campaign_count == 1
    assert response.campaigns.active_campaign_count == 1
    assert [item.model_dump(mode="json") for item in response.campaigns.items] == [
        {
            "campaign_id": campaign.id,
            "name": "Probate Wave 1",
            "status": "active",
            "member_count": 2,
            "active_member_count": 1,
            "suppressed_member_count": 1,
        }
    ]
    assert response.tasks.open_count == 1
    assert response.tasks.items[0].title == "Call interested probate lead"
    assert response.tasks.items[0].lead_id == active_lead.id
    assert [item.kind for item in response.timeline.items] == ["task", "run", "event", "event"]
    assert response.timeline.items[0].summary == "Call interested probate lead"
    assert response.timeline.items[1].summary == "lead_outbound_enrollment"
    assert response.timeline.items[2].summary == "lead.replied"
