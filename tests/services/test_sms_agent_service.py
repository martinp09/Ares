from types import SimpleNamespace

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.contacts import ContactsRepository
from app.db.conversations import ConversationsRepository
from app.db.messages import MessagesRepository
from app.models.marketing_leads import LeadUpsertRequest
from app.models.sms_agent import SmsAgentSendRequest
from app.services.inbound_sms_service import NormalizedSmsEvent
from app.services.sms_agent_service import SmsAgentService


def _service(settings: Settings, sent_requests: list[dict] | None = None) -> SmsAgentService:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return SmsAgentService(
        settings=settings,
        conversations=ConversationsRepository(client=client, settings=settings),
        messages=MessagesRepository(client=client, settings=settings),
        request_sender=(sent_requests or []).append,
    )


def test_sms_agent_dry_run_skips_provider_when_live_sends_disabled() -> None:
    sent_requests: list[dict] = []
    service = SmsAgentService(
        settings=Settings(_env_file=None, provider_live_sends_enabled=False, textgrid_from_number="3467725914"),
        request_sender=sent_requests.append,
    )

    response = service.send_message(
        SmsAgentSendRequest(
            business_id="limitless",
            environment="dev",
            to="555-123-4567",
            body="Ares dry-run SMS",
        )
    )

    assert response.dry_run is True
    assert response.status == "skipped"
    assert response.to == "+15551234567"
    assert response.log_status == "skipped_dry_run"
    assert sent_requests == []


def test_sms_agent_enqueue_inbound_reply_job_records_tenant_and_context() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    class RecordingRepository:
        def __init__(self) -> None:
            self.creates = []

        def enqueue_job(self, create):
            self.creates.append(create)
            return SimpleNamespace(id="smsjob_123")

    repository = RecordingRepository()
    service = SmsAgentService(
        settings=Settings(_env_file=None),
        sms_agent_repository=repository,
    )
    event = NormalizedSmsEvent(
        event_type="inbound",
        body="x" * 200,
        from_number="+15551234567",
        to_number="+13467725914",
        external_id="SM123",
        metadata={"business_id": "ignored", "environment": "ignored"},
    )

    job_id = service.enqueue_inbound_reply_job(
        event=event,
        lead=lead,
        provider_thread_id="thread_123",
        receipt_id="wh_123",
    )

    assert job_id == "smsjob_123"
    assert len(repository.creates) == 1
    create = repository.creates[0]
    assert create.business_id == lead.business_id
    assert create.environment == lead.environment
    assert create.provider_webhook_id == "wh_123"
    assert create.conversation_id == "thread_123"
    assert create.contact_id == lead.id
    assert create.from_number == "+15551234567"
    assert create.to_number == "+13467725914"
    assert create.metadata == {"external_id": "SM123", "body_preview": "x" * 160}


def test_sms_agent_enqueue_inbound_reply_job_skips_non_inbound_and_unknown_tenant() -> None:
    class FailingRepository:
        def enqueue_job(self, create):
            raise AssertionError("unknown tenant or non-inbound events should not enqueue jobs")

    service = SmsAgentService(
        settings=Settings(_env_file=None),
        sms_agent_repository=FailingRepository(),
    )

    assert (
        service.enqueue_inbound_reply_job(
            event=NormalizedSmsEvent(
                event_type="status",
                body="",
                from_number="+15551234567",
                to_number="+13467725914",
            ),
            lead=None,
            provider_thread_id=None,
            receipt_id=None,
        )
        is None
    )
    assert (
        service.enqueue_inbound_reply_job(
            event=NormalizedSmsEvent(
                event_type="inbound",
                body="Need details",
                from_number="+15551234567",
                to_number="+13467725914",
                metadata={},
            ),
            lead=None,
            provider_thread_id=None,
            receipt_id=None,
        )
        is None
    )


def test_sms_agent_enqueue_inbound_reply_job_skips_inbound_without_lead_even_with_tenant_metadata() -> None:
    class RecordingRepository:
        def __init__(self) -> None:
            self.creates = []

        def enqueue_job(self, create):
            self.creates.append(create)
            return SimpleNamespace(id="smsjob_123")

    repository = RecordingRepository()
    service = SmsAgentService(
        settings=Settings(_env_file=None),
        sms_agent_repository=repository,
    )

    job_id = service.enqueue_inbound_reply_job(
        event=NormalizedSmsEvent(
            event_type="inbound",
            body="Need details",
            from_number="+15551234567",
            to_number="+13467725914",
            external_id="SM123",
            metadata={"business_id": "limitless", "environment": "dev"},
        ),
        lead=None,
        provider_thread_id="thread_123",
        receipt_id="wh_123",
    )

    assert job_id is None
    assert repository.creates == []


def test_sms_agent_live_send_builds_textgrid_request_and_logs_message() -> None:
    sent_requests: list[dict] = []

    def fake_sender(request: dict) -> dict:
        sent_requests.append(request)
        return {"sid": "SM123", "status": "queued"}

    settings = Settings(
        _env_file=None,
        provider_live_sends_enabled=True,
        textgrid_account_sid="acct_123",
        textgrid_auth_token="token_123",
        textgrid_from_number="3467725914",
        textgrid_status_callback_url="https://runtime.example.com/sms-agent/webhooks/textgrid",
    )
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    service = SmsAgentService(
        settings=settings,
        conversations=ConversationsRepository(client=client, settings=settings),
        messages=MessagesRepository(client=client, settings=settings),
        request_sender=fake_sender,
    )

    response = service.send_message(
        SmsAgentSendRequest(
            business_id="limitless",
            environment="dev",
            contact_id="lead_123",
            to="555-123-4567",
            body="Ares live-gated SMS",
            sms_consent_confirmed=True,
            metadata={"lane": "general"},
        )
    )

    assert response.dry_run is False
    assert response.status == "queued"
    assert response.provider_message_id == "SM123"
    assert response.message_id is not None
    assert response.conversation_id == "SM123"
    assert response.log_status == "logged"
    assert sent_requests[0]["payload"] == {
        "Body": "Ares live-gated SMS",
        "From": "+13467725914",
        "To": "+15551234567",
        "StatusCallback": "https://runtime.example.com/sms-agent/webhooks/textgrid",
    }


def test_sms_agent_live_send_requires_textgrid_config() -> None:
    service = SmsAgentService(settings=Settings(_env_file=None, provider_live_sends_enabled=True))

    try:
        service.send_message(
            SmsAgentSendRequest(
                business_id="limitless",
                environment="dev",
                contact_id="lead_123",
                to="555-123-4567",
                body="Ares SMS",
                sms_consent_confirmed=True,
            )
        )
    except RuntimeError as exc:
        assert "TEXTGRID_ACCOUNT_SID" in str(exc)
        assert "TEXTGRID_AUTH_TOKEN" in str(exc)
        assert "TEXTGRID_FROM_NUMBER" in str(exc)
    else:
        raise AssertionError("Expected missing TextGrid config to raise")


def test_sms_agent_live_send_requires_contact_and_consent() -> None:
    service = SmsAgentService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="3467725914",
        )
    )

    try:
        service.send_message(
            SmsAgentSendRequest(
                business_id="limitless",
                environment="dev",
                to="555-123-4567",
                body="Ares SMS",
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "contact_id is required for live SMS sends"
    else:
        raise AssertionError("Expected missing contact_id to raise")

    try:
        service.send_message(
            SmsAgentSendRequest(
                business_id="limitless",
                environment="dev",
                contact_id="lead_123",
                to="555-123-4567",
                body="Ares SMS",
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "sms_consent_confirmed is required for live SMS sends"
    else:
        raise AssertionError("Expected missing consent confirmation to raise")
