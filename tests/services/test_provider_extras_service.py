from app.core.config import Settings
from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.suppression import SuppressionRepository
from app.models.campaigns import CampaignRecord
from app.models.lead_events import LeadEventRecord, ProviderWebhookReceiptRecord
from app.models.leads import LeadInterestStatus, LeadRecord, LeadSource
from app.models.suppression import SuppressionRecord
from app.services.provider_extras_service import ProviderExtrasService


def _build_service(settings: Settings) -> ProviderExtrasService:
    client = InMemoryControlPlaneClient()
    CampaignsRepository(client).upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Probate Wave 1",
            provider_name="instantly",
            provider_campaign_id="camp_inst_1",
            provider_workspace_id="wrk_1",
            email_tag_list=["probate", "vip"],
        )
    )
    CampaignsRepository(client).upsert(
        CampaignRecord(
            business_id="otherco",
            environment="prod",
            name="Out of Scope",
            provider_name="instantly",
            provider_campaign_id="camp_inst_2",
            provider_workspace_id="wrk_ignore",
            email_tag_list=["ignore"],
        )
    )
    LeadsRepository(client).upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.INSTANTLY_IMPORT,
            provider_name="instantly",
            provider_lead_id="lead_inst_1",
            provider_workspace_id="wrk_1",
            email="alex@example.com",
            first_name="Alex",
            verification_status="valid",
            lt_interest_status=LeadInterestStatus.INTERESTED,
            assigned_to="rep_1",
        )
    )
    LeadsRepository(client).upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.INSTANTLY_SYNC,
            provider_name="instantly",
            provider_lead_id="lead_inst_2",
            provider_workspace_id="wrk_2",
            email="jamie@example.com",
            first_name="Jamie",
            verification_status="catch_all",
            lt_interest_status=LeadInterestStatus.MEETING_BOOKED,
        )
    )
    LeadsRepository(client).upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            email="manual@example.com",
            first_name="Manual",
        )
    )
    LeadEventsRepository(client).append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id="lead_inst_1",
            campaign_id="camp_inst_1",
            provider_name="instantly",
            event_type="lead.label.custom",
            idempotency_key="evt-label",
        )
    )
    LeadEventsRepository(client).append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id="lead_inst_1",
            campaign_id="camp_inst_1",
            provider_name="instantly",
            event_type="lead.email.bounced",
            idempotency_key="evt-bounce",
        )
    )
    LeadEventsRepository(client).append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id="lead_inst_2",
            campaign_id="camp_inst_1",
            provider_name="instantly",
            event_type="lead.suppressed.unsubscribe",
            idempotency_key="evt-unsub",
        )
    )
    SuppressionRepository(client).upsert(
        SuppressionRecord(
            business_id="limitless",
            environment="dev",
            email="alex@example.com",
            reason="unsubscribe",
            provider_blocklist_id="block_1",
        )
    )
    ProviderWebhooksRepository(client).record(
        ProviderWebhookReceiptRecord(
            business_id="limitless",
            environment="dev",
            provider="instantly",
            event_type="reply_received",
            idempotency_key="wh_1",
            lead_email="alex@example.com",
        )
    )
    return ProviderExtrasService(settings=settings, client=client)


def test_provider_extras_service_returns_projected_instantly_snapshot() -> None:
    service = _build_service(
        Settings(
            _env_file=None,
            instantly_api_key="inst_secret_123456",
            instantly_webhook_secret="whsec_secret_654321",
        )
    )

    snapshot = service.get_instantly_snapshot(business_id="limitless", environment="dev")

    assert snapshot.provider == "instantly"
    assert snapshot.configured is True
    assert snapshot.transport_ready is True
    assert snapshot.webhook_signing_configured is True
    assert snapshot.summary.family_count == 8
    assert snapshot.summary.campaign_count == 1
    assert snapshot.summary.lead_count == 2
    assert snapshot.summary.workspace_count == 2
    assert snapshot.summary.webhook_receipt_count == 1
    assert snapshot.summary.blocklist_count == 1
    assert snapshot.labels.status == "projected"
    assert snapshot.labels.projected_record_count == 1
    assert snapshot.tags.projected_record_count == 2
    assert snapshot.tags.counts["campaigns_with_tags"] == 1
    assert snapshot.verification.counts["leads_with_verification_status"] == 2
    assert snapshot.verification.counts["distinct_statuses"] == 2
    assert snapshot.deliverability.counts["bounced_events"] == 1
    assert snapshot.deliverability.counts["unsubscribe_events"] == 1
    assert snapshot.blocklists.counts["provider_blocklists"] == 1
    assert snapshot.crm_actions.counts["actionable_leads"] == 2
    assert snapshot.crm_actions.counts["meeting_booked_leads"] == 1
    assert snapshot.workspace_resources.counts["workspace_count"] == 2
    rendered = snapshot.model_dump_json()
    assert "inst_secret_123456" not in rendered
    assert "whsec_secret_654321" not in rendered


def test_provider_extras_service_marks_snapshot_unconfigured_without_instantly_settings() -> None:
    service = _build_service(Settings(_env_file=None))

    snapshot = service.get_instantly_snapshot(business_id="limitless", environment="dev")

    assert snapshot.configured is False
    assert snapshot.transport_ready is False
    assert snapshot.webhook_signing_configured is False
    assert snapshot.labels.configured is False
    assert snapshot.tags.configured is False
    assert snapshot.verification.configured is False
    assert snapshot.deliverability.configured is False
    assert snapshot.blocklists.configured is False
    assert snapshot.inbox_placement.status == "configuration_missing"
    assert snapshot.crm_actions.configured is False
    assert snapshot.workspace_resources.configured is False
