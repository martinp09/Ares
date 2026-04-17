import pytest

from app.db.automation_runs import AutomationRunsRepository
from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.leads import LeadsRepository
from app.db.suppression import SuppressionRepository
from app.models.campaigns import CampaignRecord
from app.models.leads import LeadRecord
from app.models.suppression import SuppressionRecord, SuppressionScope, SuppressionSource
from app.providers.instantly import InstantlyClient
from app.services.campaign_lifecycle_service import CampaignLifecycleService, InactiveCampaignEnrollmentError
from app.services.lead_outbound_service import LeadOutboundService, OutboundEnrollmentRequest
from app.services.lead_suppression_service import LeadSuppressionService


def test_enqueue_leads_skips_suppressed_and_records_membership() -> None:
    store = InMemoryControlPlaneStore()
    client = InMemoryControlPlaneClient(store)
    leads_repository = LeadsRepository(client)
    campaigns_repository = CampaignsRepository(client)
    campaign_lifecycle_service = CampaignLifecycleService(campaigns_repository)
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

    campaign = campaign_lifecycle_service.create_or_upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Probate",
            provider_name="instantly",
            provider_campaign_id="camp_123",
        )
    )
    campaign = campaign_lifecycle_service.activate(campaign.id or "")

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
        campaigns_repository=campaigns_repository,
        memberships_repository=memberships_repository,
        automation_runs_repository=automation_runs_repository,
        suppression_service=suppression_service,
        campaign_lifecycle_service=campaign_lifecycle_service,
    )

    result = service.enqueue_leads(
        OutboundEnrollmentRequest(
            business_id="limitless",
            environment="dev",
            lead_ids=[live_lead.id or "", suppressed_lead.id or ""],
            campaign_id=campaign.id,
            assigned_to="owner_1",
        )
    )

    assert result.suppressed_lead_ids == [suppressed_lead.id]
    assert len(sent_batches) == 1
    assert sent_batches[0]["payload"]["campaign_id"] == campaign.id
    assert len(sent_batches[0]["payload"]["leads"]) == 1
    memberships = memberships_repository.list_for_campaign(campaign.id or "")
    assert len(memberships) == 1
    assert memberships[0].lead_id == live_lead.id
    runs = automation_runs_repository.list(business_id="limitless", environment="dev")
    statuses = {run.lead_id: run.status for run in runs}
    assert statuses[live_lead.id] == "completed"
    assert statuses[suppressed_lead.id] == "cancelled"


def test_enqueue_leads_rejects_inactive_campaigns() -> None:
    store = InMemoryControlPlaneStore()
    client = InMemoryControlPlaneClient(store)
    leads_repository = LeadsRepository(client)
    campaigns_repository = CampaignsRepository(client)
    campaign_lifecycle_service = CampaignLifecycleService(campaigns_repository)
    memberships_repository = CampaignMembershipsRepository(client)
    automation_runs_repository = AutomationRunsRepository(client)

    sent_batches: list[dict] = []
    instantly_client = InstantlyClient(
        api_key="inst_123",
        request_sender=lambda payload: sent_batches.append(payload) or {"ok": True},
        sleep_fn=lambda _: None,
    )

    campaign = campaign_lifecycle_service.create_or_upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Draft Probate",
            provider_name="instantly",
            provider_campaign_id="camp_789",
        )
    )
    lead = leads_repository.upsert(
        LeadRecord(business_id="limitless", environment="dev", email="live@example.com", first_name="Live")
    )

    service = LeadOutboundService(
        instantly_client=instantly_client,
        leads_repository=leads_repository,
        campaigns_repository=campaigns_repository,
        memberships_repository=memberships_repository,
        automation_runs_repository=automation_runs_repository,
        campaign_lifecycle_service=campaign_lifecycle_service,
    )

    with pytest.raises(InactiveCampaignEnrollmentError, match="must be active before enrollment"):
        service.enqueue_leads(
            OutboundEnrollmentRequest(
                business_id="limitless",
                environment="dev",
                lead_ids=[lead.id or ""],
                campaign_id=campaign.id,
            )
        )

    assert sent_batches == []
    assert memberships_repository.list_for_campaign(campaign.id or "") == []
    assert automation_runs_repository.list(business_id="limitless", environment="dev") == []


def test_require_active_campaign_accepts_slug_request_for_numeric_supabase_campaign(monkeypatch) -> None:
    campaigns_repository = CampaignsRepository()
    campaign_lifecycle_service = CampaignLifecycleService(campaigns_repository)
    campaign = CampaignRecord(
        id="camp_123",
        business_id="1",
        environment="dev",
        name="Remote Probate",
        status="active",
    )

    monkeypatch.setattr(campaign_lifecycle_service, "_require_campaign", lambda campaign_id: campaign)
    monkeypatch.setattr(
        "app.services.campaign_lifecycle_service.resolve_tenant",
        lambda business_id, environment: type("Tenant", (), {"business_pk": 1, "environment": "dev"})(),
    )

    resolved = campaign_lifecycle_service.require_active_campaign(
        campaign_id="camp_123",
        business_id="limitless",
        environment="dev",
    )

    assert resolved is campaign
