from fastapi.testclient import TestClient

from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.suppression import SuppressionRepository
from app.db.tasks import TasksRepository
from app.main import app, create_app
from app.services.campaign_lifecycle_service import CampaignLifecycleService
from app.services.lead_sequence_runner import LeadSequenceRunner
from app.services.lead_suppression_service import LeadSuppressionService
from app.services.lead_task_service import LeadTaskService
from app.services.lead_webhook_service import LeadWebhookService

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


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

        def intake_probate_cases(self, *, business_id: str, environment: str, payloads, keep_only: bool):
            self.calls.append((business_id, environment, payloads, keep_only))
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
            True,
        )
    ]


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
    assert outbound_request["chunk_size"] == 50
    assert outbound_request["wait_seconds"] == 1.5


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


def test_post_instantly_webhook_rejects_malformed_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/lead-machine/webhooks/instantly",
        json={"business_id": "limitless", "environment": "dev", "payload": "oops"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422


def test_create_app_mounts_lead_machine_router() -> None:
    routes = {route.path for route in create_app().routes}

    assert "/lead-machine/probate/intake" in routes
    assert "/lead-machine/outbound/enqueue" in routes
    assert "/lead-machine/webhooks/instantly" in routes
