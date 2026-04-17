from app.db.automation_runs import AutomationRunsRepository
from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.probate_leads import ProbateLeadsRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.suppression import SuppressionRepository
from app.db.tasks import TasksRepository
from app.models.campaigns import CampaignRecord
from app.models.leads import LeadLifecycleStatus, LeadRecord
from app.providers.instantly import InstantlyClient
from app.services.campaign_lifecycle_service import CampaignLifecycleService
from app.services.harris_probate_intake_service import HarrisProbateIntakeService
from app.services.lead_outbound_service import LeadOutboundService
from app.services.lead_sequence_runner import LeadSequenceRunner
from app.services.lead_suppression_service import LeadSuppressionService
from app.services.lead_task_service import LeadTaskService
from app.services.lead_webhook_service import LeadWebhookService
from app.services.probate_hcad_match_service import ProbateHCADMatchService
from app.services.probate_lead_bridge_service import ProbateLeadBridgeService
from app.services.probate_lead_score_service import ProbateLeadScoreService
from app.services.probate_write_path_service import ProbateWritePathService


def test_intake_probate_cases_persists_canonical_leads() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    leads_repository = LeadsRepository(client)
    probate_leads_repository = ProbateLeadsRepository(client)
    service = ProbateWritePathService(
        intake_service=HarrisProbateIntakeService(),
        hcad_match_service=ProbateHCADMatchService(),
        score_service=ProbateLeadScoreService(),
        probate_leads_repository=probate_leads_repository,
        lead_bridge_service=ProbateLeadBridgeService(leads_repository),
    )

    result = service.intake_probate_cases(
        business_id="limitless",
        environment="dev",
        payloads=[
            {
                "case_number": "2026-10001",
                "type": "INDEPENDENT ADMINISTRATION",
                "estate_name": "Estate of Jane Example",
                "decedent_name": "Jane Example",
            },
            {
                "case_number": "2026-10002",
                "type": "SMALL ESTATE",
                "estate_name": "Estate of Skip Row",
            },
        ],
        hcad_candidates_by_case={
            "2026-10001": [
                {
                    "acct": "00011122",
                    "owner_name": "Jane Example",
                    "mailing_address": "123 Main St, Houston, TX 77002",
                    "property_address": "456 Oak St, Houston, TX 77008",
                }
            ]
        },
    )

    assert result["received_count"] == 2
    assert result["kept_count"] == 1
    assert len(result["lead_ids"]) == 1
    probate_records = probate_leads_repository.list(business_id="limitless", environment="dev")
    assert len(probate_records) == 2
    persisted = leads_repository.get(result["lead_ids"][0])
    assert persisted is not None
    assert persisted.lifecycle_status == LeadLifecycleStatus.READY
    assert persisted.probate_case_number == "2026-10001"
    assert persisted.score is not None
    assert persisted.score > 0
    assert persisted.raw_payload["probate_lead_id"] == probate_records[0].id


def test_intake_probate_cases_applies_upstream_overlays_before_keep_filtering() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    leads_repository = LeadsRepository(client)
    probate_leads_repository = ProbateLeadsRepository(client)
    service = ProbateWritePathService(
        intake_service=HarrisProbateIntakeService(),
        hcad_match_service=ProbateHCADMatchService(),
        score_service=ProbateLeadScoreService(),
        probate_leads_repository=probate_leads_repository,
        lead_bridge_service=ProbateLeadBridgeService(leads_repository),
    )

    result = service.intake_probate_cases(
        business_id="limitless",
        environment="dev",
        payloads=[
            {
                "case_number": "2026-10003",
                "type": "SMALL ESTATE",
                "estate_name": "Estate of Jane Overlay",
                "keep_now": True,
                "hcad_match_status": "matched",
                "hcad_acct": "00033344",
                "owner_name": "Jane Overlay",
                "mailing_address": "123 Main St, Houston, TX 77002",
                "property_address": "456 Oak St, Houston, TX 77008",
                "contact_confidence": "high",
                "matched_candidate_count": 1,
                "tax_delinquent": True,
                "estate_of": True,
                "pain_stack": {"estate_of": True, "tax_delinquent": True},
            }
        ],
    )

    assert result["received_count"] == 1
    assert result["kept_count"] == 1
    assert result["processed_count"] == 1
    assert result["keep_now_count"] == 1
    assert result["bridged_count"] == 1
    assert result["records"] == [
        {
            "case_number": "2026-10003",
            "keep_now": True,
            "lead_score": 99.0,
            "hcad_match_status": "matched",
            "contact_confidence": "high",
            "bridged_lead_id": result["lead_ids"][0],
        }
    ]
    persisted = leads_repository.get(result["lead_ids"][0])
    assert persisted is not None
    assert persisted.probate_case_number == "2026-10003"
    assert persisted.custom_variables["hcad_acct"] == "00033344"
    assert persisted.custom_variables["hcad_match_status"] == "matched"
    assert persisted.custom_variables["contact_confidence"] == "high"
    assert persisted.custom_variables["tax_delinquent"] is True
    assert persisted.custom_variables["estate_of"] is True
    assert persisted.custom_variables["pain_stack"] == {"estate_of": True, "tax_delinquent": True}
    assert persisted.score == 99.0
    probate_lead = probate_leads_repository.get(persisted.raw_payload["probate_lead_id"])
    assert probate_lead is not None
    assert probate_lead.tax_delinquent is True
    assert probate_lead.estate_of is True
    assert probate_lead.pain_stack == {"estate_of": True, "tax_delinquent": True}


def test_enqueue_probate_leads_records_runs_and_memberships() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    leads_repository = LeadsRepository(client)
    campaigns_repository = CampaignsRepository(client)
    memberships_repository = CampaignMembershipsRepository(client)
    automation_runs_repository = AutomationRunsRepository(client)
    suppression_repository = SuppressionRepository(client)
    campaign_lifecycle_service = CampaignLifecycleService(campaigns_repository)
    sent_batches: list[dict] = []
    outbound_service = LeadOutboundService(
        instantly_client=InstantlyClient(
            api_key="inst_123",
            request_sender=lambda payload: sent_batches.append(payload) or {"ok": True},
            sleep_fn=lambda _: None,
        ),
        leads_repository=leads_repository,
        campaigns_repository=campaigns_repository,
        memberships_repository=memberships_repository,
        automation_runs_repository=automation_runs_repository,
        suppression_service=LeadSuppressionService(suppression_repository),
        campaign_lifecycle_service=campaign_lifecycle_service,
    )
    service = ProbateWritePathService(outbound_service=outbound_service)
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
    lead = leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            email="lead@example.com",
            first_name="Lead",
        )
    )

    result = service.enqueue_probate_leads(
        business_id="limitless",
        environment="dev",
        lead_ids=[lead.id or ""],
        campaign_id=campaign.id,
    )

    assert len(result.automation_runs) == 1
    assert len(result.memberships) == 1
    assert len(result.provider_batches) == 1
    assert len(sent_batches) == 1
    refreshed = leads_repository.get(lead.id or "")
    assert refreshed is not None
    assert refreshed.lifecycle_status == LeadLifecycleStatus.ROUTED


def test_handle_instantly_webhook_writes_receipt_then_event() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    leads_repository = LeadsRepository(client)
    lead_events_repository = LeadEventsRepository(client)
    provider_webhooks_repository = ProviderWebhooksRepository(client)
    suppression_repository = SuppressionRepository(client)
    memberships_repository = CampaignMembershipsRepository(client)
    tasks_repository = TasksRepository(client)
    campaigns_repository = CampaignsRepository(client)
    webhook_service = LeadWebhookService(
        leads_repository=leads_repository,
        lead_events_repository=lead_events_repository,
        campaigns_repository=campaigns_repository,
        memberships_repository=memberships_repository,
        provider_webhooks_repository=provider_webhooks_repository,
        suppression_service=LeadSuppressionService(suppression_repository),
        sequence_runner=LeadSequenceRunner(memberships_repository),
        task_service=LeadTaskService(tasks_repository),
        campaign_lifecycle_service=CampaignLifecycleService(campaigns_repository),
    )
    service = ProbateWritePathService(webhook_service=webhook_service)
    lead = leads_repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            email="lead@example.com",
            first_name="Lead",
        )
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

    first = service.handle_instantly_webhook(
        business_id="limitless",
        environment="dev",
        payload=payload,
    )
    second = service.handle_instantly_webhook(
        business_id="limitless",
        environment="dev",
        payload=payload,
    )

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"
    receipt = provider_webhooks_repository.get(first["receipt_id"])
    assert receipt is not None
    assert receipt.processed is True
    events = lead_events_repository.list_for_lead(lead.id or "")
    assert len(events) == 1
    assert events[0].provider_receipt_id == first["receipt_id"]
