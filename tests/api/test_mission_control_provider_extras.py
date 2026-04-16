from app.core.config import get_settings
from app.db.campaigns import CampaignsRepository
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.suppression import SuppressionRepository
from app.models.campaigns import CampaignRecord
from app.models.lead_events import LeadEventRecord, ProviderWebhookReceiptRecord
from app.models.leads import LeadInterestStatus, LeadRecord, LeadSource
from app.models.suppression import SuppressionRecord
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def _seed_instantly_projection_data() -> None:
    CampaignsRepository().upsert(
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
    LeadsRepository().upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.INSTANTLY_IMPORT,
            provider_name="instantly",
            provider_lead_id="lead_inst_1",
            provider_workspace_id="wrk_1",
            email="alex@example.com",
            verification_status="valid",
            lt_interest_status=LeadInterestStatus.INTERESTED,
            assigned_to="rep_1",
        )
    )
    LeadsRepository().upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.INSTANTLY_SYNC,
            provider_name="instantly",
            provider_lead_id="lead_inst_2",
            provider_workspace_id="wrk_2",
            email="jamie@example.com",
            verification_status="catch_all",
            lt_interest_status=LeadInterestStatus.MEETING_BOOKED,
        )
    )
    LeadEventsRepository().append(
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
    LeadEventsRepository().append(
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
    SuppressionRepository().upsert(
        SuppressionRecord(
            business_id="limitless",
            environment="dev",
            email="alex@example.com",
            reason="unsubscribe",
            provider_blocklist_id="block_1",
        )
    )
    ProviderWebhooksRepository().record(
        ProviderWebhookReceiptRecord(
            business_id="limitless",
            environment="dev",
            provider="instantly",
            event_type="reply_received",
            idempotency_key="wh_1",
            lead_email="alex@example.com",
        )
    )


def test_instantly_provider_extras_endpoint_returns_projected_snapshot(client, monkeypatch) -> None:
    reset_control_plane_state()
    _seed_instantly_projection_data()
    monkeypatch.setenv("INSTANTLY_API_KEY", "inst_secret_123456")
    monkeypatch.setenv("INSTANTLY_WEBHOOK_SECRET", "whsec_secret_654321")
    get_settings.cache_clear()

    response = client.get(
        "/mission-control/providers/instantly/extras?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "instantly"
    assert body["configured"] is True
    assert body["transport_ready"] is True
    assert body["webhook_signing_configured"] is True
    assert body["summary"]["campaign_count"] == 1
    assert body["summary"]["lead_count"] == 2
    assert body["summary"]["workspace_count"] == 2
    assert body["summary"]["webhook_receipt_count"] == 1
    assert body["tags"]["projected_record_count"] == 2
    assert body["verification"]["counts"]["distinct_statuses"] == 2
    assert body["blocklists"]["counts"]["provider_blocklists"] == 1
    assert body["crm_actions"]["counts"]["actionable_leads"] == 2
    assert "inst_secret_123456" not in response.text
    assert "whsec_secret_654321" not in response.text


def test_instantly_provider_extras_endpoint_reflects_missing_configuration(client) -> None:
    reset_control_plane_state()
    get_settings.cache_clear()

    response = client.get(
        "/mission-control/providers/instantly/extras?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["transport_ready"] is False
    assert body["webhook_signing_configured"] is False
    assert body["labels"]["status"] == "configuration_missing"
    assert body["inbox_placement"]["status"] == "configuration_missing"
