from app.db.automation_runs import AutomationRunsRepository
from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.leads import LeadsRepository
from app.db.suppression import SuppressionRepository
from app.models.leads import LeadRecord
from app.models.suppression import SuppressionRecord, SuppressionScope, SuppressionSource
from app.providers.instantly import InstantlyClient
from app.services.lead_outbound_service import LeadOutboundService, OutboundEnrollmentRequest
from app.services.lead_suppression_service import LeadSuppressionService


def test_enqueue_leads_skips_suppressed_and_records_membership() -> None:
    store = InMemoryControlPlaneStore()
    client = InMemoryControlPlaneClient(store)
    leads_repository = LeadsRepository(client)
    memberships_repository = CampaignMembershipsRepository(client)
    automation_runs_repository = AutomationRunsRepository(client)
    suppression_repository = SuppressionRepository(client)
    suppression_service = LeadSuppressionService(suppression_repository)

    sent_batches: list[dict] = []
    instantly_client = InstantlyClient(
        api_key="inst_123",
        request_sender=lambda payload: sent_batches.append(payload) or {"ok": True},
        sleep_fn=lambda _: None,
    )

    live_lead = leads_repository.upsert(
        LeadRecord(business_id="limitless", environment="dev", email="live@example.com", first_name="Live")
    )
    suppressed_lead = leads_repository.upsert(
        LeadRecord(business_id="limitless", environment="dev", email="stop@example.com", first_name="Stop")
    )
    suppression_repository.upsert(
        SuppressionRecord(
            business_id="limitless",
            environment="dev",
            lead_id=suppressed_lead.id,
            email=suppressed_lead.email,
            scope=SuppressionScope.GLOBAL,
            reason="manual",
            source=SuppressionSource.MANUAL,
        )
    )

    service = LeadOutboundService(
        instantly_client=instantly_client,
        leads_repository=leads_repository,
        memberships_repository=memberships_repository,
        automation_runs_repository=automation_runs_repository,
        suppression_service=suppression_service,
    )

    result = service.enqueue_leads(
        OutboundEnrollmentRequest(
            business_id="limitless",
            environment="dev",
            lead_ids=[live_lead.id or "", suppressed_lead.id or ""],
            campaign_id="camp_123",
            assigned_to="owner_1",
        )
    )

    assert result.suppressed_lead_ids == [suppressed_lead.id]
    assert len(sent_batches) == 1
    assert sent_batches[0]["payload"]["campaign_id"] == "camp_123"
    assert len(sent_batches[0]["payload"]["leads"]) == 1
    memberships = memberships_repository.list_for_campaign("camp_123")
    assert len(memberships) == 1
    assert memberships[0].lead_id == live_lead.id
    runs = automation_runs_repository.list(business_id="limitless", environment="dev")
    statuses = {run.lead_id: run.status for run in runs}
    assert statuses[live_lead.id] == "completed"
    assert statuses[suppressed_lead.id] == "cancelled"
