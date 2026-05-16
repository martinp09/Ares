import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.suppression import SuppressionRepository
from app.core.config import get_settings
from app.db.tasks import TasksRepository
from app.main import app, create_app
from app.services.campaign_lifecycle_service import CampaignLifecycleService
from app.services.lead_sequence_runner import LeadSequenceRunner
from app.services.lead_suppression_service import LeadSuppressionService
from app.services.lead_task_service import LeadTaskService
from app.services.lead_webhook_service import LeadWebhookService

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def _instantly_signature(secret: str, raw_body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def build_webhook_service() -> LeadWebhookService:
    store = InMemoryControlPlaneStore()
    client = InMemoryControlPlaneClient(store)
    memberships_repository = CampaignMembershipsRepository(client)
    campaigns_repository = CampaignsRepository(client)
    return LeadWebhookService(
        leads_repository=LeadsRepository(client),
        lead_events_repository=LeadEventsRepository(client),
        campaigns_repository=campaigns_repository,
        memberships_repository=memberships_repository,
        provider_webhooks_repository=ProviderWebhooksRepository(client),
        suppression_service=LeadSuppressionService(SuppressionRepository(client)),
        sequence_runner=LeadSequenceRunner(memberships_repository),
        task_service=LeadTaskService(TasksRepository(client)),
        campaign_lifecycle_service=CampaignLifecycleService(campaigns_repository),
    )


def test_post_probate_intake_normalizes_scores_and_bridges_keep_now(monkeypatch) -> None:
    class StubWritePathService:
        def __init__(self) -> None:
            self.calls = []

        def intake_probate_cases(
            self,
            *,
            business_id: str,
            environment: str,
            payloads,
            hcad_candidates_by_case=None,
            keep_only: bool,
        ):
            self.calls.append((business_id, environment, payloads, hcad_candidates_by_case, keep_only))
            return {
                "processed_count": 1,
                "keep_now_count": 1,
                "bridged_count": 1,
                "records": [
                    {
                        "case_number": "2026-11111",
                        "keep_now": True,
                        "lead_score": 91.0,
                        "hcad_match_status": "matched",
                        "contact_confidence": "high",
                        "bridged_lead_id": "lead_2026-11111",
                    }
                ],
            }

    from app.api import lead_machine as lead_machine_api

    stub = StubWritePathService()
    monkeypatch.setattr(lead_machine_api, "_build_write_path_service", lambda: stub)
    client = TestClient(app)

    response = client.post(
        "/lead-machine/probate/intake",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "records": [
                {
                    "case_number": "2026-11111",
                    "filing_type": "INDEPENDENT ADMINISTRATION",
                    "keep_now": True,
                    "hcad_candidates": [{"account": "123"}],
                },
                {
                    "case_number": "2026-22222",
                    "filing_type": "SMALL ESTATE",
                    "keep_now": False,
                },
            ],
            "keep_only": True,
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    assert response.json() == {
        "processed_count": 1,
        "keep_now_count": 1,
        "bridged_count": 1,
        "records": [
            {
                "case_number": "2026-11111",
                "keep_now": True,
                "lead_score": 91.0,
                "hcad_match_status": "matched",
                "contact_confidence": "high",
                "bridged_lead_id": "lead_2026-11111",
            }
        ],
    }
    assert stub.calls == [
        (
            "limitless",
            "dev",
            [
                {
                    "case_number": "2026-11111",
                    "filing_type": "INDEPENDENT ADMINISTRATION",
                    "keep_now": True,
                    "hcad_candidates": [{"account": "123"}],
                },
                {
                    "case_number": "2026-22222",
                    "filing_type": "SMALL ESTATE",
                    "keep_now": False,
                    "hcad_candidates": [],
                },
            ],
            {"2026-11111": [{"account": "123"}]},
            True,
        )
    ]


def test_harris_daily_import_endpoint_dry_runs_without_provider_send(monkeypatch) -> None:
    class StubDailyLeadMachineService:
        def __init__(self) -> None:
            self.calls = []

        def run_daily_import(
            self,
            *,
            business_id,
            environment,
            run_date,
            probate_records,
            hcad_estate_of_records,
            dry_run,
            keep_only,
        ):
            self.calls.append(
                (business_id, environment, run_date.isoformat(), probate_records, hcad_estate_of_records, dry_run, keep_only)
            )
            return {
                "run_key": f"harris-daily-lead-machine:{run_date.isoformat()}",
                "run_date": run_date.isoformat(),
                "dry_run": dry_run,
                "live_send_policy": "no_provider_sends_or_slack_posts_from_daily_import",
                "counts": {"provider_send_count": 0, "qc_warning_count": 0},
                "probate": {"received_count": len(probate_records), "records": []},
                "estate_of": {"received_count": len(hcad_estate_of_records), "records": []},
                "qc_warnings": [],
                "notifications": [{"type": "daily_digest", "status": "skipped_missing_token"}],
            }

    from app.api import lead_machine as lead_machine_api

    stub = StubDailyLeadMachineService()
    monkeypatch.setattr(lead_machine_api, "_build_daily_lead_machine_service", lambda: stub)
    client = TestClient(app)

    response = client.post(
        "/lead-machine/harris/daily-import",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "run_date": "2026-05-09",
            "dry_run": True,
            "probate_records": [
                {
                    "case_number": "2026-10001",
                    "filing_type": "INDEPENDENT ADMINISTRATION",
                    "hcad_candidates": [{"acct": "123"}],
                }
            ],
            "hcad_estate_of_records": [
                {"hcad_account": "1234567890123", "owner_name": "Estate Of Jane Example"}
            ],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["run_key"] == "harris-daily-lead-machine:2026-05-09"
    assert body["counts"]["provider_send_count"] == 0
    assert body["notifications"][0]["status"] == "skipped_missing_token"
    assert stub.calls == [
        (
            "limitless",
            "dev",
            "2026-05-09",
            [
                {
                    "case_number": "2026-10001",
                    "filing_type": "INDEPENDENT ADMINISTRATION",
                    "hcad_candidates": [{"acct": "123"}],
                }
            ],
            [{"hcad_account": "1234567890123", "owner_name": "Estate Of Jane Example"}],
            True,
            True,
        )
    ]


def test_harris_daily_import_endpoint_requires_at_least_one_source_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/lead-machine/harris/daily-import",
        json={"business_id": "limitless", "environment": "dev", "run_date": "2026-05-09"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422


def test_post_lead_machine_intake_creates_canonical_lead_and_event() -> None:
    from app.api import lead_machine as lead_machine_api

    store = InMemoryControlPlaneStore()
    client_state = InMemoryControlPlaneClient(store)
    service = lead_machine_api.lead_intake_service.__class__(
        leads_repository=LeadsRepository(client_state),
        lead_events_repository=LeadEventsRepository(client_state),
    )
    original = lead_machine_api.lead_intake_service
    lead_machine_api.lead_intake_service = service
    try:
        client = TestClient(app)
        response = client.post(
            "/lead-machine/intake",
            json={
                "business_id": "limitless",
                "environment": "dev",
                "source": "manual",
                "source_record_id": "lp_123",
                "campaign_key": "lease-option",
                "first_name": "Maya",
                "phone": "+15551234567",
                "email": "maya@example.com",
                "property_address": "123 Main St",
                "county": "Harris",
                "status": "ready",
                "pipeline_stage": "new_inbound",
                "priority": "high",
                "metadata": {"utm_source": "site"},
            },
            headers=AUTH_HEADERS,
        )
    finally:
        lead_machine_api.lead_intake_service = original

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "created"
    assert body["lead_id"].startswith("lead_")
    assert body["event_id"].startswith("levt_")
    assert body["queued"] is False
    assert body["skipped"] is False
    assert body["failed_side_effects"] == []


def test_post_lead_machine_intake_returns_deduped_for_replayed_identity(monkeypatch) -> None:
    from app.api import lead_machine as lead_machine_api

    store = InMemoryControlPlaneStore()
    client_state = InMemoryControlPlaneClient(store)
    service = lead_machine_api.lead_intake_service.__class__(
        leads_repository=LeadsRepository(client_state),
        lead_events_repository=LeadEventsRepository(client_state),
    )
    monkeypatch.setattr(lead_machine_api, "lead_intake_service", service)
    client = TestClient(app)
    payload = {
        "business_id": "limitless",
        "environment": "dev",
        "source_record_id": "lp_123",
        "phone": "+15551234567",
    }

    first = client.post("/lead-machine/intake", json=payload, headers=AUTH_HEADERS)
    second = client.post("/lead-machine/intake", json=payload, headers=AUTH_HEADERS)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["status"] == "created"
    assert second.json()["status"] == "deduped"
    assert first.json()["lead_id"] == second.json()["lead_id"]


def test_post_probate_intake_rejects_empty_records_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/lead-machine/probate/intake",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "records": [],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "records"]


def test_post_probate_intake_rejects_missing_required_record_fields() -> None:
    client = TestClient(app)

    response = client.post(
        "/lead-machine/probate/intake",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "records": [{"estate_name": "Estate of Broken"}],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422


def test_post_probate_property_tax_title_enrichment_runs_no_send_gate() -> None:
    client = TestClient(app)

    response = client.post(
        "/lead-machine/internal/probate-property-tax-title-enrichment",
        headers=AUTH_HEADERS,
        json={
            "business_id": "limitless",
            "environment": "dev",
            "keep_now_rows": [
                {
                    "case_number": "2026-PTT-1",
                    "filing_type": "APP TO DETERMINE HEIRSHIP",
                    "estate_name": "Estate of Jane Example",
                    "decedent_name": "Jane Example",
                    "keep_now": True,
                }
            ],
            "hcad_candidates_by_case": {
                "2026-PTT-1": [
                    {
                        "acct": "000123400001",
                        "owner_name": "Example Jane",
                        "mailing_address": "123 MAIN ST",
                        "property_address": "456 OAK ST",
                    }
                ]
            },
            "tax_overlays_by_account": {
                "123400001": {
                    "status": "tax_overlay_verified_delinquent",
                    "is_delinquent": True,
                    "amount_owed": 5250.75,
                    "account": "123400001",
                    "confidence": "high",
                    "search_method": "local_snapshot",
                }
            },
            "land_record_rows_by_case": {
                "2026-PTT-1": [
                    {"instrument_number": "RP-1", "instrument_type": "Affidavit of Heirship"}
                ]
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["no_send"] is True
    assert payload["provider_sends_enabled"] is False
    assert payload["outbound_allowed"] is False
    assert payload["property_match_completed_count"] == 1
    assert payload["tax_overlay_completed_count"] == 1
    assert payload["title_friction_review_count"] == 1
    assert payload["records"][0]["tax_delinquent"] is True


def test_post_probate_property_tax_title_enrichment_rejects_live_flags() -> None:
    client = TestClient(app)

    response = client.post(
        "/lead-machine/internal/probate-property-tax-title-enrichment",
        headers=AUTH_HEADERS,
        json={
            "business_id": "limitless",
            "environment": "dev",
            "keep_now_rows": [],
            "live_land_record_calls": True,
        },
    )

    assert response.status_code == 422
    assert "enrichment_approval.approved=true" in response.json()["detail"]


def test_post_outbound_enqueue_returns_ids_from_service_result(monkeypatch) -> None:
    class StubWritePathService:
        def __init__(self) -> None:
            self.calls = []

        def enqueue_probate_leads(self, **kwargs):
            self.calls.append(kwargs)
            return type(
                "Result",
                (),
                {
                    "automation_runs": [type("Run", (), {"id": "run_123"})(), type("Run", (), {"id": "run_456"})()],
                    "memberships": [type("Membership", (), {"id": "mship_123"})()],
                    "suppressed_lead_ids": ["lead_sup_1"],
                    "provider_batches": [{"ok": True}],
                },
            )()

    from app.api import lead_machine as lead_machine_api

    stub = StubWritePathService()
    monkeypatch.setattr(lead_machine_api, "_build_write_path_service", lambda: stub)
    client = TestClient(app)

    response = client.post(
        "/lead-machine/outbound/enqueue",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "lead_ids": ["lead_1", "lead_2"],
            "campaign_id": "camp_1",
            "assigned_to": "agent_7",
            "verify_leads_on_import": True,
            "operator_approval": True,
            "chunk_size": 50,
            "wait_seconds": 1.5,
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "automation_run_ids": ["run_123", "run_456"],
        "membership_ids": ["mship_123"],
        "suppressed_lead_ids": ["lead_sup_1"],
        "provider_batches": [{"ok": True}],
    }
    assert len(stub.calls) == 1
    outbound_request = stub.calls[0]
    assert outbound_request["business_id"] == "limitless"
    assert outbound_request["environment"] == "dev"
    assert outbound_request["lead_ids"] == ["lead_1", "lead_2"]
    assert outbound_request["campaign_id"] == "camp_1"
    assert outbound_request["assigned_to"] == "agent_7"
    assert outbound_request["verify_leads_on_import"] is True
    assert outbound_request["operator_approval"] is True
    assert outbound_request["chunk_size"] == 50
    assert outbound_request["wait_seconds"] == 1.5


def test_post_outbound_enqueue_blocks_without_operator_approval_before_provider_configuration() -> None:
    client = TestClient(app)

    response = client.post(
        "/lead-machine/outbound/enqueue",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "lead_ids": ["lead_1"],
            "campaign_id": "camp_1",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 503
    assert "Explicit operator approval" in response.json()["detail"]
    assert "INSTANTLY_API_KEY" not in response.json()["detail"]


def test_post_instantly_webhook_records_headers_and_trust_metadata(monkeypatch) -> None:
    class StubWritePathService:
        def __init__(self) -> None:
            self.calls = []

        def handle_instantly_webhook(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "status": "processed",
                "receipt_id": "wh_123",
                "event_id": "evt_123",
                "lead_id": "lead_123",
                "suppression_id": None,
                "membership_id": None,
                "task_id": "task_123",
                "notification": None,
            }

    from app.api import lead_machine as lead_machine_api

    stub = StubWritePathService()
    monkeypatch.setattr(lead_machine_api, "_build_write_path_service", lambda: stub)
    client = TestClient(app)

    response = client.post(
        "/lead-machine/webhooks/instantly",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "payload": {
                "event_type": "email_sent",
                "campaign_id": "camp_123",
                "lead_email": "lane@example.com",
            },
        },
        headers={**AUTH_HEADERS, "x-instantly-signature": "sig_123"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "processed",
        "receipt_id": "wh_123",
        "event_id": "evt_123",
        "lead_id": "lead_123",
        "suppression_id": None,
        "membership_id": None,
        "task_id": "task_123",
    }
    assert len(stub.calls) == 1
    assert stub.calls[0]["business_id"] == "limitless"
    assert stub.calls[0]["environment"] == "dev"
    assert stub.calls[0]["payload"]["event_type"] == "email_sent"
    assert stub.calls[0]["trusted"] is False
    assert stub.calls[0]["trust_reason"] == "signature_present_unverified"


def test_post_instantly_webhook_accepts_raw_provider_payload_with_tenant_query(monkeypatch) -> None:
    class StubWritePathService:
        def __init__(self) -> None:
            self.calls = []

        def handle_instantly_webhook(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "status": "processed",
                "receipt_id": "wh_123",
                "event_id": "evt_123",
                "lead_id": "lead_123",
                "suppression_id": None,
                "membership_id": None,
                "task_id": None,
            }

    from app.api import lead_machine as lead_machine_api

    stub = StubWritePathService()
    monkeypatch.setattr(lead_machine_api, "_build_write_path_service", lambda: stub)
    client = TestClient(app)

    response = client.post(
        "/lead-machine/webhooks/instantly?business_id=limitless&environment=prod",
        json={
            "event_type": "reply_received",
            "campaign_id": "camp_123",
            "lead_email": "lane@example.com",
        },
        headers={**AUTH_HEADERS, "x-instantly-signature": "sig_123"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert len(stub.calls) == 1
    assert stub.calls[0]["business_id"] == "limitless"
    assert stub.calls[0]["environment"] == "prod"
    assert stub.calls[0]["payload"]["event_type"] == "reply_received"
    assert stub.calls[0]["trusted"] is False
    assert stub.calls[0]["trust_reason"] == "signature_present_unverified"


def test_post_instantly_webhook_rejects_client_supplied_trust_metadata(monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_WEBHOOK_SIGNATURES_REQUIRED", "false")
    get_settings.cache_clear()
    client = TestClient(app)

    try:
        response = client.post(
            "/lead-machine/webhooks/instantly",
            json={
                "business_id": "limitless",
                "environment": "dev",
                "payload": {"event_type": "email_sent"},
                "trusted": True,
                "trust_reason": "caller_claimed_trust",
            },
            headers=AUTH_HEADERS,
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 422


def test_post_instantly_webhook_requires_secret_when_signatures_required(monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_WEBHOOK_SIGNATURES_REQUIRED", "true")
    monkeypatch.delenv("INSTANTLY_WEBHOOK_SECRET", raising=False)
    get_settings.cache_clear()
    client = TestClient(app)

    try:
        response = client.post(
            "/lead-machine/webhooks/instantly",
            json={
                "business_id": "limitless",
                "environment": "dev",
                "payload": {"event_type": "email_sent"},
            },
            headers=AUTH_HEADERS,
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Instantly webhook secret is required"


def test_post_instantly_webhook_accepts_valid_server_verified_signature(monkeypatch) -> None:
    class StubWritePathService:
        def __init__(self) -> None:
            self.calls = []

        def handle_instantly_webhook(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "status": "processed",
                "receipt_id": "wh_signed",
                "event_id": "evt_signed",
                "lead_id": "lead_signed",
                "suppression_id": None,
                "membership_id": None,
                "task_id": None,
            }

    from app.api import lead_machine as lead_machine_api

    stub = StubWritePathService()
    monkeypatch.setattr(lead_machine_api, "_build_write_path_service", lambda: stub)
    monkeypatch.setenv("PROVIDER_WEBHOOK_SIGNATURES_REQUIRED", "true")
    monkeypatch.setenv("INSTANTLY_WEBHOOK_SECRET", "instantly-webhook-secret")
    get_settings.cache_clear()
    raw_body = json.dumps(
        {
            "business_id": "limitless",
            "environment": "dev",
            "payload": {"event_type": "reply_received", "lead_email": "seller@example.com"},
        },
        separators=(",", ":"),
    ).encode("utf-8")
    client = TestClient(app)

    try:
        response = client.post(
            "/lead-machine/webhooks/instantly",
            content=raw_body,
            headers={
                **AUTH_HEADERS,
                "content-type": "application/json",
                "x-instantly-signature": _instantly_signature("instantly-webhook-secret", raw_body),
            },
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["receipt_id"] == "wh_signed"
    assert stub.calls[0]["trusted"] is True
    assert stub.calls[0]["trust_reason"] == "signature_verified"


def test_post_instantly_webhook_is_replay_safe(monkeypatch) -> None:
    from app.api import lead_machine as lead_machine_api

    class StubWritePathService:
        def __init__(self, service: LeadWebhookService) -> None:
            self.service = service

        def handle_instantly_webhook(self, **kwargs):
            return self.service.handle_instantly_webhook(**kwargs)

    stub_service = StubWritePathService(build_webhook_service())
    monkeypatch.setattr(lead_machine_api, "_build_write_path_service", lambda: stub_service)
    client = TestClient(app)
    payload = {
        "business_id": "limitless",
        "environment": "dev",
        "payload": {
            "event_type": "email_sent",
            "timestamp": "2026-04-16T17:00:00Z",
            "campaign_id": "camp_123",
            "campaign_name": "Probate Wave",
            "lead_email": "lane@example.com",
            "email_id": "msg_123",
            "step": 1,
        },
    }

    first = client.post("/lead-machine/webhooks/instantly", json=payload, headers=AUTH_HEADERS)
    second = client.post("/lead-machine/webhooks/instantly", json=payload, headers=AUTH_HEADERS)

    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert second.json()["receipt_id"] == first.json()["receipt_id"]
    assert second.json()["event_id"] == first.json()["event_id"]


def test_post_instantly_webhook_preserves_slack_notification(monkeypatch) -> None:
    class StubWritePathService:
        def handle_instantly_webhook(self, **kwargs):
            return {
                "status": "processed",
                "receipt_id": "wh_reply",
                "event_id": "levt_reply",
                "lead_id": "lead_reply",
                "suppression_id": "supp_reply",
                "membership_id": "mship_reply",
                "task_id": None,
                "notification": {
                    "route": "instantly_replies",
                    "status": "sent",
                    "deduped": False,
                    "channel_id": "C-INSTANTLY-REPLIES",
                    "dedupe_key": "instantly:levt_reply",
                    "slack_message_ts": "1715788800.000100",
                    "error_message": None,
                },
            }

    from app.api import lead_machine as lead_machine_api

    monkeypatch.setattr(lead_machine_api, "_build_write_path_service", lambda: StubWritePathService())
    client = TestClient(app)

    response = client.post(
        "/lead-machine/webhooks/instantly",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "payload": {
                "event_type": "reply_received",
                "timestamp": "2026-04-16T17:05:00Z",
                "campaign_id": "camp_123",
                "campaign_name": "Probate Wave",
                "lead_email": "lane@example.com",
                "email_id": "msg_124",
                "reply_text": "Please call me.",
            },
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["notification"] == {
        "route": "instantly_replies",
        "status": "sent",
        "deduped": False,
        "channel_id": "C-INSTANTLY-REPLIES",
        "dedupe_key": "instantly:levt_reply",
        "slack_message_ts": "1715788800.000100",
        "error_message": None,
    }


def test_post_instantly_webhook_rejects_malformed_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/lead-machine/webhooks/instantly",
        json={"business_id": "limitless", "environment": "dev", "payload": "oops"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422


def test_post_followup_step_runner_delegates_to_sequence_dispatch(monkeypatch) -> None:
    from app.api import lead_machine as lead_machine_api

    class StubSuppressionService:
        def is_suppressed(self, **kwargs):
            self.kwargs = kwargs
            return False

    class StubInboundSmsService:
        def dispatch_lease_option_sequence_step(self, request):
            self.request = request
            return {"message_id": "msg_123", "channel": request.channel, "status": "queued"}

    suppression_stub = StubSuppressionService()
    inbound_stub = StubInboundSmsService()
    monkeypatch.setattr(lead_machine_api, "lead_suppression_service", suppression_stub)
    monkeypatch.setattr(lead_machine_api, "inbound_sms_service", inbound_stub)
    client = TestClient(app)

    response = client.post(
        "/lead-machine/internal/followup-step-runner",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "lead_id": "lead_123",
            "day": 4,
            "channel": "email",
            "template_id": "followup_day_4_email",
            "manual_call_checkpoint": True,
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "message_id": "msg_123",
        "channel": "email",
        "status": "queued",
        "suppressed": False,
    }
    assert suppression_stub.kwargs == {
        "business_id": "limitless",
        "environment": "dev",
        "lead_id": "lead_123",
        "email": None,
        "campaign_id": None,
    }
    assert inbound_stub.request.business_id == "limitless"
    assert inbound_stub.request.environment == "dev"
    assert inbound_stub.request.lead_id == "lead_123"
    assert inbound_stub.request.day == 4
    assert inbound_stub.request.channel == "email"
    assert inbound_stub.request.template_id == "followup_day_4_email"
    assert inbound_stub.request.manual_call_checkpoint is True


def test_post_suppression_sync_records_lead_and_membership_suppression(monkeypatch) -> None:
    from app.api import lead_machine as lead_machine_api

    class StubSuppressionService:
        def apply_event(self, **kwargs):
            self.kwargs = kwargs
            return type("Suppression", (), {"id": "sup_123", "reason": "bounced", "active": True})()

    class StubSequenceRunner:
        def handle_event(self, **kwargs):
            self.kwargs = kwargs
            return type("Membership", (), {"id": "mem_123", "status": "suppressed"})()

    suppression_stub = StubSuppressionService()
    sequence_stub = StubSequenceRunner()
    monkeypatch.setattr(lead_machine_api, "lead_suppression_service", suppression_stub)
    monkeypatch.setattr(lead_machine_api, "lead_sequence_runner", sequence_stub)
    client = TestClient(app)

    response = client.post(
        "/lead-machine/internal/suppression-sync",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "lead_id": "lead_123",
            "campaign_id": "camp_123",
            "event_type": "lead.email.bounced",
            "lead_email": "lead@example.com",
            "provider_name": "instantly",
            "provider_event_id": "evt_123",
            "idempotency_key": "sup-evt-123",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "processed",
        "suppression_id": "sup_123",
        "reason": "bounced",
        "active": True,
        "event_type": "lead.email.bounced",
    }
    assert suppression_stub.kwargs["business_id"] == "limitless"
    assert suppression_stub.kwargs["lead_id"] == "lead_123"
    assert suppression_stub.kwargs["campaign_id"] == "camp_123"
    assert suppression_stub.kwargs["event"].event_type == "lead.email.bounced"
    assert sequence_stub.kwargs["business_id"] == "limitless"
    assert sequence_stub.kwargs["lead_id"] == "lead_123"
    assert sequence_stub.kwargs["campaign_id"] == "camp_123"
    assert sequence_stub.kwargs["event"].event_type == "lead.email.bounced"


def test_post_task_reminder_or_overdue_creates_reminder_task(monkeypatch) -> None:
    from app.api import lead_machine as lead_machine_api

    class StubTasksRepository:
        def __init__(self) -> None:
            self.calls = []

        def create(self, record, *, dedupe_key=None):
            self.calls.append((record, dedupe_key))
            return type("Task", (), {"id": "tsk_123", "status": record.status, "deduped": False})()

    stub_repo = StubTasksRepository()
    monkeypatch.setattr(lead_machine_api, "tasks_repository", stub_repo)
    client = TestClient(app)

    response = client.post(
        "/lead-machine/internal/task-reminder-or-overdue",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "task_id": "task_123",
            "lead_id": "lead_123",
            "task_title": "Call lead about probate follow-up",
            "due_at": "2026-04-16T17:00:00Z",
            "status": "open",
            "assigned_to": "sierra",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "reminded",
        "reminder_task_id": "tsk_123",
        "overdue": True,
        "reminder_created": True,
    }
    record, dedupe_key = stub_repo.calls[0]
    assert record.business_id == "limitless"
    assert record.environment == "dev"
    assert record.lead_id == "lead_123"
    assert record.title == "Reminder: Call lead about probate follow-up"
    assert record.task_type == "follow_up"
    assert dedupe_key == "task-reminder:task_123"


def test_create_app_mounts_lead_machine_router() -> None:
    routes = {route.path for route in create_app().routes}

    assert "/lead-machine/intake" in routes
    assert "/lead-machine/probate/intake" in routes
    assert "/lead-machine/internal/probate-property-tax-title-enrichment" in routes
    assert "/lead-machine/outbound/enqueue" in routes
    assert "/lead-machine/webhooks/instantly" in routes
    assert "/lead-machine/internal/followup-step-runner" in routes
    assert "/lead-machine/internal/suppression-sync" in routes
    assert "/lead-machine/internal/task-reminder-or-overdue" in routes
