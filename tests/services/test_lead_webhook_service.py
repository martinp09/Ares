from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.opportunities import OpportunitiesRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.suppression import SuppressionRepository
from app.db.tasks import TasksRepository
from app.models.campaigns import CampaignRecord, CampaignStatus
from app.models.leads import LeadLifecycleStatus, LeadRecord
from app.models.opportunities import OpportunitySourceLane, OpportunityStage
from app.services.campaign_lifecycle_service import CampaignLifecycleService
from app.services.lead_sequence_runner import LeadSequenceRunner
from app.services.lead_suppression_service import LeadSuppressionService
from app.services.lead_task_service import LeadTaskService
from app.services.lead_webhook_service import LeadWebhookService
from app.services.opportunity_service import OpportunityService


def build_service() -> tuple[
    LeadWebhookService,
    LeadsRepository,
    LeadEventsRepository,
    TasksRepository,
    SuppressionRepository,
    CampaignMembershipsRepository,
    CampaignsRepository,
    CampaignLifecycleService,
]:
    store = InMemoryControlPlaneStore()
    client = InMemoryControlPlaneClient(store)
    leads_repository = LeadsRepository(client)
    lead_events_repository = LeadEventsRepository(client)
    tasks_repository = TasksRepository(client)
    suppression_repository = SuppressionRepository(client)
    memberships_repository = CampaignMembershipsRepository(client)
    campaigns_repository = CampaignsRepository(client)
    campaign_lifecycle_service = CampaignLifecycleService(campaigns_repository)
    opportunity_service = OpportunityService(OpportunitiesRepository(client))
    service = LeadWebhookService(
        leads_repository=leads_repository,
        lead_events_repository=lead_events_repository,
        campaigns_repository=campaigns_repository,
        memberships_repository=memberships_repository,
        provider_webhooks_repository=ProviderWebhooksRepository(client),
        suppression_service=LeadSuppressionService(suppression_repository),
        sequence_runner=LeadSequenceRunner(memberships_repository),
        task_service=LeadTaskService(tasks_repository),
        campaign_lifecycle_service=campaign_lifecycle_service,
        opportunity_service=opportunity_service,
    )
    return (
        service,
        leads_repository,
        lead_events_repository,
        tasks_repository,
        suppression_repository,
        memberships_repository,
        campaigns_repository,
        campaign_lifecycle_service,
    )


def test_email_sent_webhook_creates_canonical_event_and_single_task() -> None:
    service, leads_repository, lead_events_repository, tasks_repository, _, memberships_repository, _, _ = build_service()
    lead = leads_repository.upsert(
        LeadRecord(business_id="limitless", environment="dev", email="lead@example.com", first_name="Lane")
    )

    payload = {
        "event_type": "email_sent",
        "timestamp": "2026-04-16T17:00:00Z",
        "campaign_id": "camp_123",
        "campaign_name": "Probate Wave",
        "lead_email": "lead@example.com",
        "email_id": "msg_123",
        "step": 1,
    }

    first = service.handle_instantly_webhook(business_id="limitless", environment="dev", payload=payload)
    second = service.handle_instantly_webhook(business_id="limitless", environment="dev", payload=payload)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"
    events = lead_events_repository.list_for_lead(lead.id or "")
    assert [event.event_type for event in events] == ["lead.email.sent"]
    tasks = tasks_repository.list_for_lead(lead.id or "")
    assert len(tasks) == 1
    assert tasks[0].task_type == "manual_call"
    memberships = memberships_repository.list_for_lead(lead.id or "")
    assert memberships[0].status == "active"


def test_reply_webhook_suppresses_lead_without_creating_task() -> None:
    service, leads_repository, lead_events_repository, tasks_repository, suppression_repository, memberships_repository, _, _ = build_service()
    lead = leads_repository.upsert(
        LeadRecord(business_id="limitless", environment="dev", email="lead@example.com", first_name="Lane")
    )

    payload = {
        "event_type": "reply_received",
        "timestamp": "2026-04-16T17:05:00Z",
        "campaign_id": "camp_123",
        "campaign_name": "Probate Wave",
        "lead_email": "lead@example.com",
        "email_id": "msg_124",
    }

    result = service.handle_instantly_webhook(business_id="limitless", environment="dev", payload=payload)

    assert result["status"] == "processed"
    assert tasks_repository.list_for_lead(lead.id or "") == []
    suppressions = suppression_repository.list_active(business_id="limitless", environment="dev")
    assert len(suppressions) == 1
    assert suppressions[0].reason == "replied"
    refreshed = leads_repository.get(lead.id or "")
    assert refreshed is not None
    assert refreshed.lifecycle_status == LeadLifecycleStatus.SUPPRESSED
    assert refreshed.reply_count == 1
    assert lead_events_repository.list_for_lead(lead.id or "")[0].event_type == "lead.reply.received"
    memberships = memberships_repository.list_for_lead(lead.id or "")
    assert memberships[0].status == "suppressed"


def test_reply_webhook_reuses_existing_email_lead_even_when_identity_key_is_external() -> None:
    service, leads_repository, lead_events_repository, _, suppression_repository, _, _, _ = build_service()
    lead = leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            external_key="probate:2026-12345",
            email="lead@example.com",
            first_name="Lane",
        )
    )

    result = service.handle_instantly_webhook(
        business_id="limitless",
        environment="dev",
        payload={
            "event_type": "reply_received",
            "timestamp": "2026-04-16T17:05:00Z",
            "campaign_id": "camp_123",
            "campaign_name": "Probate Wave",
            "lead_email": "lead@example.com",
            "email_id": "msg_124",
        },
    )

    assert result["status"] == "processed"
    assert result["lead_id"] == lead.id
    assert len(leads_repository.list(business_id="limitless", environment="dev")) == 1
    assert lead_events_repository.list_for_lead(lead.id or "")[0].event_type == "lead.reply.received"
    assert suppression_repository.list_active(business_id="limitless", environment="dev")[0].lead_id == lead.id


def test_positive_probate_events_create_or_update_opportunity() -> None:
    service, leads_repository, _, _, _, _, _, _ = build_service()
    lead = leads_repository.upsert(
        LeadRecord(business_id="limitless", environment="dev", email="lead@example.com", first_name="Lane")
    )

    reply_result = service.handle_instantly_webhook(
        business_id="limitless",
        environment="dev",
        payload={
            "event_type": "reply_received",
            "timestamp": "2026-04-16T17:05:00Z",
            "campaign_id": "camp_123",
            "campaign_name": "Probate Wave",
            "lead_email": "lead@example.com",
            "email_id": "msg_124",
        },
    )
    interested_result = service.handle_instantly_webhook(
        business_id="limitless",
        environment="dev",
        payload={
            "event_type": "lead_interested",
            "timestamp": "2026-04-16T17:06:00Z",
            "campaign_id": "camp_123",
            "campaign_name": "Probate Wave",
            "lead_email": "lead@example.com",
            "email_id": "msg_125",
        },
    )

    repository = OpportunitiesRepository(service.lead_events_repository.client)
    opportunities = repository.list(business_id="limitless", environment="dev")

    assert reply_result["status"] == "processed"
    assert interested_result["status"] == "processed"
    assert len(opportunities) == 1
    assert opportunities[0].lead_id == lead.id
    assert opportunities[0].source_lane == OpportunitySourceLane.PROBATE
    assert opportunities[0].stage == OpportunityStage.QUALIFIED_OPPORTUNITY
    assert opportunities[0].metadata["campaign_name"] == "Probate Wave"
    assert opportunities[0].metadata["last_event_type"] == "lead.status.interested"
    assert opportunities[0].metadata["campaign_id"]


def test_campaign_completed_webhook_completes_campaign_and_is_duplicate_safe() -> None:
    service, leads_repository, lead_events_repository, tasks_repository, suppression_repository, memberships_repository, campaigns_repository, campaign_lifecycle_service = build_service()
    campaign = campaign_lifecycle_service.create_or_upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Probate Wave",
            provider_name="instantly",
            provider_campaign_id="camp_123",
        )
    )
    campaign = campaign_lifecycle_service.activate(campaign.id or "")
    assert campaign.status == CampaignStatus.ACTIVE

    payload = {
        "event_type": "campaign_completed",
        "timestamp": "2026-04-16T17:10:00Z",
        "campaign_id": "camp_123",
        "campaign_name": "Probate Wave",
        "lead_email": "lead@example.com",
        "email_id": "msg_125",
    }

    first = service.handle_instantly_webhook(business_id="limitless", environment="dev", payload=payload)
    second = service.handle_instantly_webhook(business_id="limitless", environment="dev", payload=payload)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"
    refreshed_campaign = campaigns_repository.get(campaign.id or "")
    assert refreshed_campaign is not None
    assert refreshed_campaign.id == campaign.id
    assert refreshed_campaign.status == CampaignStatus.COMPLETED
    lead_events = lead_events_repository.list_for_lead(first["lead_id"])
    assert [event.event_type for event in lead_events] == ["campaign.completed"]
    refreshed_lead = leads_repository.get(first["lead_id"])
    assert refreshed_lead is not None
    assert refreshed_lead.lifecycle_status == LeadLifecycleStatus.CLOSED
    memberships = memberships_repository.list_for_lead(first["lead_id"])
    assert len(memberships) == 1
    assert memberships[0].campaign_id == campaign.id
    assert memberships[0].status == "completed"
    assert tasks_repository.list_for_lead(first["lead_id"]) == []
    assert suppression_repository.list_active(business_id="limitless", environment="dev") == []
