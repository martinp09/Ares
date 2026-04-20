from datetime import UTC, datetime, timedelta

from app.db.automation_runs import AutomationRunsRepository
from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_events import LeadEventsRepository
from app.db.contacts import ContactsRepository
from app.db.leads import LeadsRepository
from app.db.opportunities import OpportunitiesRepository
from app.db.tasks import TasksRepository
from app.models.automation_runs import AutomationRunRecord, AutomationRunStatus
from app.models.campaigns import CampaignMembershipRecord, CampaignMembershipStatus, CampaignRecord, CampaignStatus
from app.models.lead_events import LeadEventRecord
from app.models.leads import LeadInterestStatus, LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.marketing_leads import LeadUpsertRequest
from app.models.mission_control import MissionControlContactRecord, MissionControlMessageRecord, MissionControlThreadRecord
from app.models.opportunities import OpportunityRecord, OpportunitySourceLane, OpportunityStage
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


def test_get_dashboard_groups_opportunities_by_lane_and_stage() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    opportunities_repository = OpportunitiesRepository(client)
    service = MissionControlService(client=client, opportunities_repository=opportunities_repository)

    opportunities_repository.upsert(
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane=OpportunitySourceLane.PROBATE,
            lead_id="lead_1",
            stage=OpportunityStage.QUALIFIED_OPPORTUNITY,
        )
    )
    opportunities_repository.upsert(
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane=OpportunitySourceLane.LEASE_OPTION_INBOUND,
            contact_id="contact_1",
            stage=OpportunityStage.QUALIFIED_OPPORTUNITY,
        )
    )

    dashboard = service.get_dashboard(business_id="limitless", environment="dev")

    assert dashboard.opportunity_count == 2
    assert [item.model_dump(mode="json") for item in dashboard.opportunity_stage_summaries or []] == [
        {"source_lane": "lease_option_inbound", "stage": "qualified_opportunity", "count": 1},
        {"source_lane": "probate", "stage": "qualified_opportunity", "count": 1},
    ]
    assert dashboard.outbound_probate_summary is None
    assert dashboard.inbound_lease_option_summary is None
    assert dashboard.opportunity_pipeline_summary is not None
    assert dashboard.opportunity_pipeline_summary.total_opportunity_count == 2
    assert [item.model_dump(mode="json") for item in dashboard.opportunity_pipeline_summary.lane_stage_summaries] == [
        {"source_lane": "lease_option_inbound", "stage": "qualified_opportunity", "count": 1},
        {"source_lane": "probate", "stage": "qualified_opportunity", "count": 1},
    ]



def test_mission_control_task_actions_update_threads_leads_and_tasks() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    leads_repository = LeadsRepository(client)
    campaigns_repository = CampaignsRepository(client)
    memberships_repository = CampaignMembershipsRepository(client)
    tasks_repository = TasksRepository(client)
    service = MissionControlService(
        client=client,
        leads_repository=leads_repository,
        campaigns_repository=campaigns_repository,
        campaign_memberships_repository=memberships_repository,
        tasks_repository=tasks_repository,
    )
    base_time = datetime(2026, 4, 17, 16, 0, tzinfo=UTC)

    campaign = campaigns_repository.upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Call Back Wave",
            status=CampaignStatus.ACTIVE,
            created_at=base_time,
            updated_at=base_time,
        )
    )
    lead = leads_repository.upsert(
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
    memberships_repository.upsert(
        CampaignMembershipRecord(
            business_id="limitless",
            environment="dev",
            lead_id=lead.id,
            campaign_id=campaign.id,
            status=CampaignMembershipStatus.ACTIVE,
            subscribed_at=base_time,
        )
    )
    task = tasks_repository.create(
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
    thread = MissionControlThreadRecord(
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
    service.upsert_thread_projection(thread)

    complete_response = service.complete_task_for_thread(
        thread_id=thread.id,
        notes="Called and left a voicemail.",
        follow_up_outcome="left_voicemail",
    )

    assert complete_response.thread_id == thread.id
    assert complete_response.completed_task_count == 1
    updated_task = tasks_repository.get(task.id)
    assert updated_task is not None
    assert updated_task.status == TaskStatus.COMPLETED
    assert updated_task.details["operator_notes"] == "Called and left a voicemail."
    assert updated_task.details["follow_up_outcome"] == "left_voicemail"
    stored_thread = service._require_thread_projection(thread.id)
    assert stored_thread.context.get("manual_call_due_at") is None
    assert stored_thread.context["reply_needs_review"] is False
    assert stored_thread.context["task_completion_note"] == "Called and left a voicemail."
    assert stored_thread.context["follow_up_outcome"] == "left_voicemail"

    review_task = tasks_repository.create(
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

    suppress_response = service.suppress_thread(thread_id=thread.id, reason="do_not_contact", note="owner requested")
    assert suppress_response.action == "suppressed"
    suppressed_lead = leads_repository.get(lead.id)
    assert suppressed_lead is not None
    assert suppressed_lead.lifecycle_status == LeadLifecycleStatus.SUPPRESSED
    membership = memberships_repository.list_for_lead(lead.id)[0]
    assert membership.status == CampaignMembershipStatus.SUPPRESSED
    cancelled_task = tasks_repository.get(task.id)
    assert cancelled_task is not None
    assert cancelled_task.status == TaskStatus.COMPLETED
    cancelled_review_task = tasks_repository.get(review_task.id)
    assert cancelled_review_task is not None
    assert cancelled_review_task.status == TaskStatus.CANCELLED
    assert cancelled_review_task.details["suppression_reason"] == "do_not_contact"
    suppressed_thread = service._require_thread_projection(thread.id)
    assert suppressed_thread.context["sequence_status"] == "suppressed"
    assert suppressed_thread.context.get("manual_call_due_at") is None
    assert suppressed_thread.context["reply_needs_review"] is False
    assert suppressed_thread.context["suppression_reason"] == "do_not_contact"

    unsuppress_response = service.unsuppress_thread(thread_id=thread.id, note="reinstated")
    assert unsuppress_response.action == "unsuppressed"
    restored_lead = leads_repository.get(lead.id)
    assert restored_lead is not None
    assert restored_lead.lifecycle_status == LeadLifecycleStatus.ACTIVE
    restored_membership = memberships_repository.list_for_lead(lead.id)[0]
    assert restored_membership.status == CampaignMembershipStatus.ACTIVE
    assert restored_membership.unsubscribed_at is None
    restored_thread = service._require_thread_projection(thread.id)
    assert restored_thread.context["sequence_status"] == "active"
    assert restored_thread.context.get("suppression_reason") is None
    assert restored_thread.context.get("suppressed_at") is None


def test_complete_task_for_booked_thread_with_ready_outcome_advances_lease_option_opportunity() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts_repository = ContactsRepository(client)
    opportunities_repository = OpportunitiesRepository(client)
    service = MissionControlService(
        client=client,
        opportunities_repository=opportunities_repository,
    )
    base_time = datetime(2026, 4, 17, 18, 0, tzinfo=UTC)
    contact = contacts_repository.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Ready Contact",
            phone="+15559990000",
            email="ready-contact@example.com",
            property_address="123 Main St, Houston, TX",
            booking_status="booked",
        )
    )
    service.opportunity_service.create_for_contact(
        business_id=contact.business_id,
        environment=contact.environment,
        contact_id=contact.id,
        source_lane=OpportunitySourceLane.LEASE_OPTION_INBOUND,
    )
    thread = MissionControlThreadRecord(
        business_id="limitless",
        environment="dev",
        channel="sms",
        status="open",
        unread_count=1,
        contact=MissionControlContactRecord(
            display_name="Ready Contact",
            phone=contact.phone,
            email=contact.email,
        ),
        messages=[
            MissionControlMessageRecord(
                direction="inbound",
                channel="sms",
                body="Let's move forward.",
                created_at=base_time + timedelta(minutes=1),
            )
        ],
        context={
            "lead_id": contact.id,
            "booking_status": "booked",
            "sequence_status": "active",
            "reply_needs_review": True,
        },
        created_at=base_time,
        updated_at=base_time,
    )
    service.upsert_thread_projection(thread)

    service.complete_task_for_thread(
        thread_id=thread.id,
        notes="Qualified and ready to proceed.",
        follow_up_outcome="ready_for_offer",
    )

    opportunities = opportunities_repository.list(business_id="limitless", environment="dev")

    assert len(opportunities) == 1
    assert opportunities[0].source_lane == OpportunitySourceLane.LEASE_OPTION_INBOUND
    assert opportunities[0].contact_id == contact.id
    assert opportunities[0].stage == OpportunityStage.OFFER_PATH_SELECTED


def test_contact_backed_thread_actions_resolve_marketing_contacts_and_restore_booking_status() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts_repository = ContactsRepository(client)
    opportunities_repository = OpportunitiesRepository(client)
    tasks_repository = TasksRepository(client)
    service = MissionControlService(
        client=client,
        opportunities_repository=opportunities_repository,
    )
    base_time = datetime(2026, 4, 17, 19, 0, tzinfo=UTC)
    contact = contacts_repository.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Lease Contact",
            phone="+155****9012",
            email="lease-contact@example.com",
            property_address="456 Oak Ave, Houston, TX",
            booking_status="booked",
        )
    )
    manual_task = tasks_repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            lead_id=contact.id,
            title="Call lease-option contact",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_CALL,
            priority=TaskPriority.HIGH,
            idempotency_key="task-contact-call",
            details={"source": "mission_control"},
            created_at=base_time,
        )
    )
    review_task = tasks_repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            lead_id=contact.id,
            title="Review lease-option reply",
            status=TaskStatus.OPEN,
            task_type=TaskType.SUPPRESSION_REVIEW,
            priority=TaskPriority.NORMAL,
            idempotency_key="task-contact-review",
            details={"source": "mission_control"},
            created_at=base_time,
        )
    )
    thread = MissionControlThreadRecord(
        business_id="limitless",
        environment="dev",
        channel="sms",
        status="open",
        unread_count=1,
        contact=MissionControlContactRecord(
            display_name="Lease Contact",
            phone=contact.phone,
            email=contact.email,
        ),
        messages=[
            MissionControlMessageRecord(
                direction="inbound",
                channel="sms",
                body="We’re ready to talk.",
                created_at=base_time + timedelta(minutes=1),
            )
        ],
        context={
            "lead_id": contact.id,
            "booking_status": "booked",
            "sequence_status": "active",
            "reply_needs_review": True,
        },
        created_at=base_time,
        updated_at=base_time,
    )
    service.upsert_thread_projection(thread)

    complete_response = service.complete_task_for_thread(
        thread_id=thread.id,
        notes="Qualified and ready to proceed.",
        follow_up_outcome="ready_for_offer",
    )
    assert complete_response.completed_task_count == 1
    assert tasks_repository.get(manual_task.id).status == TaskStatus.COMPLETED
    assert tasks_repository.get(review_task.id).status == TaskStatus.OPEN
    opportunities = opportunities_repository.list(business_id="limitless", environment="dev")
    assert len(opportunities) == 1
    assert opportunities[0].source_lane == OpportunitySourceLane.LEASE_OPTION_INBOUND
    assert opportunities[0].contact_id == contact.id
    assert opportunities[0].stage == OpportunityStage.OFFER_PATH_SELECTED

    suppress_response = service.suppress_thread(thread_id=thread.id, reason="do_not_contact", note="owner requested")
    assert suppress_response.action == "suppressed"
    suppressed_contact = contacts_repository.get_lead(contact.id)
    assert suppressed_contact is not None
    assert suppressed_contact.booking_status == "cancelled"
    assert tasks_repository.get(review_task.id).status == TaskStatus.CANCELLED
    refreshed_thread = service._require_thread_projection(thread.id)
    assert refreshed_thread.context["sequence_status"] == "suppressed"
    assert refreshed_thread.context["booking_status"] == "cancelled"
    assert refreshed_thread.context["booking_status_before_suppression"] == "booked"

    unsuppress_response = service.unsuppress_thread(thread_id=thread.id, note="reinstated")
    assert unsuppress_response.action == "unsuppressed"
    restored_contact = contacts_repository.get_lead(contact.id)
    assert restored_contact is not None
    assert restored_contact.booking_status == "booked"
    restored_thread = service._require_thread_projection(thread.id)
    assert restored_thread.context["sequence_status"] == "active"
    assert restored_thread.context["booking_status"] == "booked"
    assert restored_thread.context.get("booking_status_before_suppression") is None
