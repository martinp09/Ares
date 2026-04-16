from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.suppression import SuppressionRepository
from app.db.tasks import TasksRepository
from app.models.leads import LeadLifecycleStatus, LeadRecord
from app.services.lead_sequence_runner import LeadSequenceRunner
from app.services.lead_suppression_service import LeadSuppressionService
from app.services.lead_task_service import LeadTaskService
from app.services.lead_webhook_service import LeadWebhookService


def build_service() -> tuple[LeadWebhookService, LeadsRepository, LeadEventsRepository, TasksRepository, SuppressionRepository, CampaignMembershipsRepository]:
    store = InMemoryControlPlaneStore()
    client = InMemoryControlPlaneClient(store)
    leads_repository = LeadsRepository(client)
    lead_events_repository = LeadEventsRepository(client)
    tasks_repository = TasksRepository(client)
    suppression_repository = SuppressionRepository(client)
    memberships_repository = CampaignMembershipsRepository(client)
    service = LeadWebhookService(
        leads_repository=leads_repository,
        lead_events_repository=lead_events_repository,
        memberships_repository=memberships_repository,
        provider_webhooks_repository=ProviderWebhooksRepository(client),
        suppression_service=LeadSuppressionService(suppression_repository),
        sequence_runner=LeadSequenceRunner(memberships_repository),
        task_service=LeadTaskService(tasks_repository),
    )
    return service, leads_repository, lead_events_repository, tasks_repository, suppression_repository, memberships_repository


def test_email_sent_webhook_creates_canonical_event_and_single_task() -> None:
    service, leads_repository, lead_events_repository, tasks_repository, _, memberships_repository = build_service()
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
    service, leads_repository, lead_events_repository, tasks_repository, suppression_repository, memberships_repository = build_service()
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
