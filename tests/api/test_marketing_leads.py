import json
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.contacts import ContactsRepository
from app.db.conversations import ConversationsRepository
from app.db.messages import MessagesRepository
from app.db.tasks import TasksRepository
from app.main import app
from app.services.mission_control_service import MissionControlService
from app.models.mission_control import MissionControlTasksResponse
from app.services.marketing_lead_service import (
    LeadIntakePayload,
    MarketingLeadService,
    _ConfiguredCalBookingLinkProvider,
    _ConfiguredResendEmailGateway,
    _ConfiguredTextgridSmsGateway,
    _NoopEmailGateway,
    _NoopSmsGateway,
)

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_post_marketing_leads_returns_lead_booking_shape(monkeypatch) -> None:
    class StubLeadService:
        def __init__(self) -> None:
            self.calls = []

        def intake_lead(self, request):
            self.calls.append(request)
            return {
                "lead_id": "lead_123",
                "booking_status": "pending",
                "booking_url": "https://cal.com/lease-option/lead_123",
            }

    from app.api import marketing as marketing_api

    stub = StubLeadService()
    monkeypatch.setattr(marketing_api, "marketing_lead_service", stub)
    client = TestClient(app)

    response = client.post(
        "/marketing/leads",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "first_name": "Maya",
            "phone": "+15551234567",
            "email": "maya@example.com",
            "property_address": "123 Main St, Houston, TX",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    assert response.json() == {
        "lead_id": "lead_123",
        "booking_status": "pending",
        "booking_url": "https://cal.com/lease-option/lead_123",
    }
    assert len(stub.calls) == 1


def test_post_marketing_leads_rejects_invalid_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/marketing/leads",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "first_name": "Maya",
            "property_address": "123 Main St, Houston, TX",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422


def test_marketing_lead_service_uses_settings_backed_gateways_when_configured() -> None:
    service = MarketingLeadService(
        settings=Settings(
            _env_file=None,
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="+13467725914",
            resend_api_key="re_123",
            resend_from_email="Hermes <team@example.com>",
            cal_booking_url="https://cal.com/limitless/lease-option-review",
        )
    )

    assert isinstance(service.sms_gateway, _ConfiguredTextgridSmsGateway)
    assert isinstance(service.email_gateway, _ConfiguredResendEmailGateway)
    assert isinstance(service.booking_link_provider, _ConfiguredCalBookingLinkProvider)


def test_marketing_lead_service_dispatches_configured_provider_requests() -> None:
    sent_requests: list[dict[str, object]] = []

    class StubLeadRepository:
        def upsert_lead(self, payload: LeadIntakePayload) -> str:
            return "lead_abc123"

    service = MarketingLeadService(
        settings=Settings(
            _env_file=None,
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="+13467725914",
            textgrid_sms_url="https://api.textgrid.com/custom/messages",
            textgrid_status_callback_url="https://runtime.example.com/marketing/webhooks/textgrid",
            resend_api_key="re_123",
            resend_from_email="Hermes <team@example.com>",
            cal_booking_url="https://cal.com/limitless/lease-option-review",
        ),
        lead_repository=StubLeadRepository(),
        request_sender=sent_requests.append,
    )

    result = service.intake_lead(
        LeadIntakePayload(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    assert len(sent_requests) == 2
    assert sent_requests[0]["endpoint"] == "https://api.textgrid.com/custom/messages"
    assert sent_requests[0]["payload"] == {
        "Body": "Thanks Maya, we got your lease-option request and will follow up shortly.",
        "From": "+13467725914",
        "StatusCallback": "https://runtime.example.com/marketing/webhooks/textgrid",
        "To": "+15551234567",
    }
    assert sent_requests[1]["endpoint"] == "https://api.resend.com/emails"
    assert sent_requests[1]["payload"] == {
        "from": "Hermes <team@example.com>",
        "to": ["maya@example.com"],
        "subject": "Thanks for your lease-option inquiry",
        "text": "Thanks Maya, we got your lease-option request and will follow up shortly.",
    }
    assert parse_qs(urlparse(result["booking_url"]).query)["lead_id"] == ["lead_abc123"]


def test_marketing_lead_service_keeps_noop_gateways_without_provider_settings() -> None:
    service = MarketingLeadService(settings=Settings(_env_file=None))

    assert isinstance(service.sms_gateway, _NoopSmsGateway)
    assert isinstance(service.email_gateway, _NoopEmailGateway)


def test_settings_accepts_existing_provider_env_aliases(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "Cal_API_key=cal_alias_123",
                "TEXTGRID_FROM_NUMBER=3462891390",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.cal_api_key == "cal_alias_123"
    assert settings.textgrid_from_number == "3462891390"


def test_marketing_lead_service_dispatches_trigger_non_booker_check_over_http(monkeypatch) -> None:
    from app.services import marketing_lead_service as marketing_lead_service_module

    captured_request = {}

    class StubLeadRepository:
        def upsert_lead(self, payload) -> str:
            assert payload.business_id == "limitless"
            return "lead_123"

    class StubResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"id": "run_123"}).encode("utf-8")

    def fake_urlopen(request, timeout: int):
        captured_request["url"] = request.full_url
        captured_request["method"] = request.get_method()
        captured_request["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured_request["body"] = json.loads(request.data.decode("utf-8"))
        captured_request["timeout"] = timeout
        return StubResponse()

    monkeypatch.setenv("TRIGGER_SECRET_KEY", "tr_dev_123")
    monkeypatch.delenv("TRIGGER_API_URL", raising=False)
    monkeypatch.delenv("TRIGGER_NON_BOOKER_CHECK_TASK_ID", raising=False)
    monkeypatch.setattr(marketing_lead_service_module.request, "urlopen", fake_urlopen)

    service = marketing_lead_service_module.MarketingLeadService(
        settings=Settings(_env_file=None),
        lead_repository=StubLeadRepository(),
    )

    result = service.intake_lead(
        marketing_lead_service_module.LeadIntakePayload(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    assert result["lead_id"] == "lead_123"
    assert captured_request == {
        "url": "https://api.trigger.dev/api/v1/tasks/marketing-check-submitted-lead-booking/trigger",
        "method": "POST",
        "headers": {
            "authorization": "Bearer tr_dev_123",
            "content-type": "application/json",
        },
        "body": {
            "payload": {
                "leadId": "lead_123",
                "businessId": "limitless",
                "environment": "dev",
            },
            "options": {
                "delay": "5m",
            },
        },
        "timeout": 5,
    }


def test_marketing_lead_service_persists_lead_even_if_provider_requests_fail(monkeypatch) -> None:
    from app.services import marketing_lead_service as marketing_lead_service_module

    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())

    class StubLeadRepository:
        def upsert_lead(self, payload) -> str:
            return "lead_123"

    def fail_request(_payload):
        raise RuntimeError("provider down")

    monkeypatch.setattr(
        marketing_lead_service_module.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider down")),
    )

    service = MarketingLeadService(
        settings=Settings(
            _env_file=None,
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="+13467725914",
            resend_api_key="re_123",
            resend_from_email="Hermes <team@example.com>",
            trigger_secret_key="tr_dev_123",
        ),
        lead_repository=StubLeadRepository(),
        request_sender=fail_request,
        tasks=TasksRepository(client),
    )

    result = service.intake_lead(
        LeadIntakePayload(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    assert result["lead_id"] == "lead_123"
    assert result["side_effects"] == [
        {
            "name": "confirmation_sms",
            "status": "failed",
            "error_message": "provider down",
        },
        {
            "name": "confirmation_email",
            "status": "failed",
            "error_message": "provider down",
        },
        {
            "name": "trigger_non_booker_check",
            "status": "failed",
            "error_message": "provider down",
        },
    ]
    tasks = TasksRepository(client).list(lead_id="lead_123")
    assert [task.task_type.value for task in tasks] == ["manual_review", "manual_review", "manual_review"]
    assert [task.details["side_effect"] for task in tasks] == [
        "confirmation_sms",
        "confirmation_email",
        "trigger_non_booker_check",
    ]
    visible_tasks = MissionControlService(client=client).get_visible_provider_failure_tasks(
        business_id="limitless",
        environment="dev",
    )
    assert [task.id for task in visible_tasks] == [task.id for task in tasks]
    mission_control_tasks = MissionControlService(client=client).get_tasks(
        business_id="limitless",
        environment="dev",
    )
    assert isinstance(mission_control_tasks, MissionControlTasksResponse)
    assert mission_control_tasks.due_count == 3
    assert [task.provider_failure for task in mission_control_tasks.tasks] == [True, True, True]
    dashboard = MissionControlService(client=client).get_dashboard(
        business_id="limitless",
        environment="dev",
    )
    assert dashboard.provider_failure_task_count == 3
    assert dashboard.system_status == "watch"


def test_marketing_lead_service_logs_provider_message_ids_for_status_callbacks() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    conversations = ConversationsRepository(client)
    messages_repository = MessagesRepository(client)

    class StubLeadRepository:
        def upsert_lead(self, payload) -> str:
            return "lead_123"

    def fake_send(outbound_request):
        if outbound_request["headers"]["Content-Type"] == "application/x-www-form-urlencoded":
            return {"sid": "SM123"}
        return {"id": "email_123"}

    service = MarketingLeadService(
        settings=Settings(
            _env_file=None,
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="+13467725914",
            resend_api_key="re_123",
            resend_from_email="Hermes <team@example.com>",
        ),
        lead_repository=StubLeadRepository(),
        request_sender=fake_send,
        contacts=contacts,
        conversations=conversations,
        messages=messages_repository,
        tasks=TasksRepository(client),
    )

    result = service.intake_lead(
        LeadIntakePayload(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    assert result["lead_id"] == "lead_123"
    with client.transaction() as store:
        messages = list(getattr(store, "marketing_message_rows", {}).values())
    assert [(message.channel, message.external_message_id) for message in messages] == [
        ("sms", "SM123"),
        ("email", "email_123"),
    ]
