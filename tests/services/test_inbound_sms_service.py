from __future__ import annotations

import base64
import hashlib
import hmac

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.contacts import ContactsRepository
from app.db.conversations import ConversationsRepository
from app.db.sequences import SequencesRepository
from app.db.tasks import TasksRepository
from app.models.conversations import ConversationRecord
from app.models.marketing_leads import LeadUpsertRequest
from app.models.sequences import SequenceEnrollmentStatus
from app.providers.textgrid import normalize_incoming_webhook
from app.services.inbound_sms_service import InboundSmsService, NormalizedSmsEvent


class _StubTextgridAdapter:
    def __init__(self, *, event: NormalizedSmsEvent) -> None:
        self.event = event

    def verify_signature(self, payload, *, signature, request_url=None):
        return True

    def normalize(self, payload):
        return self.event


class _StubSequenceService:
    def __init__(self) -> None:
        self.stop_calls: list[str] = []
        self.pause_calls: list[str] = []

    def stop(self, *, phone_number: str) -> None:
        self.stop_calls.append(phone_number)

    def pause(self, *, phone_number: str) -> None:
        self.pause_calls.append(phone_number)


class _StubMessageRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def append_inbound_message(self, event: NormalizedSmsEvent, *, lead, provider_thread_id=None) -> None:
        self.calls.append((lead.id, provider_thread_id))


class _ScopedConversationRepository:
    def __init__(self, *, conversation: ConversationRecord) -> None:
        self.conversation = conversation
        self.scoped_calls: list[tuple[str, str, str, str]] = []
        self.global_calls: list[tuple[str, str]] = []

    def find_by_provider_thread(self, *, business_id: str, environment: str, channel: str, provider_thread_id: str):
        self.scoped_calls.append((business_id, environment, channel, provider_thread_id))
        return self.conversation

    def find_all_by_provider_thread(self, *, channel: str, provider_thread_id: str):
        self.global_calls.append((channel, provider_thread_id))
        raise AssertionError("global provider-thread lookup should not be used when tenant scope is available")


class _NoGlobalProviderThreadRepository:
    def __init__(self) -> None:
        self.global_calls: list[tuple[str, str]] = []

    def find_by_provider_thread(self, *, business_id: str, environment: str, channel: str, provider_thread_id: str):
        raise AssertionError("scoped provider-thread lookup should not be used without tenant metadata")

    def find_all_by_provider_thread(self, *, channel: str, provider_thread_id: str):
        self.global_calls.append((channel, provider_thread_id))
        raise AssertionError("unscoped provider-thread lookup should not be used")


def _twilio_style_signature(secret: str, url: str, payload: dict[str, object]) -> str:
    data = url + "".join(str(payload[key]) for key in sorted(payload))
    digest = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")

def test_inbound_sms_stop_reply_does_not_mutate_sequence_when_phone_is_ambiguous() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    first_lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )
    contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="other-biz",
            environment="dev",
            first_name="Alex",
            phone="+15551234567",
            email="alex@example.com",
            property_address="987 Oak St, Houston, TX",
        )
    )

    sequence = _StubSequenceService()
    service = InboundSmsService(
        textgrid_adapter=_StubTextgridAdapter(
            event=NormalizedSmsEvent(
                event_type="inbound",
                body="stop",
                from_number=first_lead.phone,
                to_number="+13445556666",
                external_id="sms_ambiguous_1",
                metadata={},
            )
        ),
        sequence_service=sequence,
        contacts=contacts,
    )

    result = service.handle_textgrid_webhook({}, signature=None)

    assert result["status"] == "processed"
    assert result["action"] == "stop"
    assert sequence.stop_calls == []
    assert sequence.pause_calls == []
    tasks = TasksRepository(client).list()
    assert len(tasks) == 1
    assert tasks[0].task_type.value == "manual_review"
    with client.transaction() as store:
        receipts = getattr(store, "provider_webhooks", {})
        assert len(receipts) == 1
        assert next(iter(receipts.values())).processed is True


def test_inbound_sms_service_skips_live_backend_review_writes_without_tenant_metadata() -> None:
    class FailingTasksRepository:
        def create(self, *args, **kwargs):
            raise AssertionError("tasks.create should not run without tenant metadata in live backend mode")

    class RecordingWebhookReceipts:
        def __init__(self) -> None:
            self.calls = []

        def record_textgrid_event(self, *, event, lead, payload):
            self.calls.append((event, lead, payload))
            raise AssertionError("record_textgrid_event should not run without tenant metadata in live backend mode")

        def mark_processed(self, receipt_id):
            raise AssertionError("mark_processed should not run when no receipt was recorded")

    service = InboundSmsService(
        settings=Settings(lead_machine_backend="supabase"),
        textgrid_adapter=_StubTextgridAdapter(
            event=NormalizedSmsEvent(
                event_type="inbound",
                body="Need help",
                from_number="+155****0000",
                to_number="+134****6666",
                external_id="sms_unknown_meta_1",
                metadata={},
            )
        ),
        webhook_receipts=RecordingWebhookReceipts(),
    )
    service.tasks = FailingTasksRepository()

    result = service.handle_textgrid_webhook(
        {"From": "+155****0000", "To": "+134****6666", "Body": "Need help"},
        signature="sig",
        request_url="https://runtime.example.com/marketing/webhooks/textgrid",
    )

    assert result == {"status": "processed", "event_type": "inbound", "action": "qualify"}


def test_inbound_sms_resolves_provider_thread_using_tenant_scope_before_phone_fallback() -> None:
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
    conversation = ConversationRecord(
        business_id=lead.business_id,
        environment=lead.environment,
        contact_id=lead.id,
        channel="sms",
        provider_thread_id="thread_123",
    )
    conversations = _ScopedConversationRepository(conversation=conversation)
    sequence = _StubSequenceService()
    messages = _StubMessageRepository()
    service = InboundSmsService(
        textgrid_adapter=_StubTextgridAdapter(
            event=NormalizedSmsEvent(
                event_type="inbound",
                body="stop",
                from_number="+15550000000",
                to_number="+13445556666",
                external_id="sms_thread_1",
                metadata={
                    "provider_thread_id": "thread_123",
                    "business_id": lead.business_id,
                    "environment": lead.environment,
                },
            )
        ),
        contacts=contacts,
        conversations=conversations,
        sequence_service=sequence,
        message_repository=messages,
    )

    result = service.handle_textgrid_webhook({}, signature=None)

    assert result["status"] == "processed"
    assert result["action"] == "stop"
    assert conversations.scoped_calls == [(lead.business_id, lead.environment, "sms", "thread_123")]
    assert conversations.global_calls == []
    assert sequence.stop_calls == [lead.phone]
    assert sequence.pause_calls == []
    assert messages.calls == [(lead.id, "thread_123")]


def test_inbound_sms_resolves_duplicate_provider_thread_ids_using_tenant_scope() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    conversations = ConversationsRepository(client)
    target = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )
    other = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="other-biz",
            environment="dev",
            first_name="Alex",
            phone="+15557654321",
            email="alex@example.com",
            property_address="987 Oak St, Houston, TX",
        )
    )
    conversations.get_or_create(
        business_id=target.business_id,
        environment=target.environment,
        contact_id=target.id,
        channel="sms",
        provider_thread_id="thread_123",
    )
    conversations.get_or_create(
        business_id=other.business_id,
        environment=other.environment,
        contact_id=other.id,
        channel="sms",
        provider_thread_id="thread_123",
    )

    messages = _StubMessageRepository()
    sequence = _StubSequenceService()
    service = InboundSmsService(
        textgrid_adapter=_StubTextgridAdapter(
            event=NormalizedSmsEvent(
                event_type="inbound",
                body="stop",
                from_number="+15550000000",
                to_number="+13445556666",
                external_id="sms_thread_duplicate_1",
                metadata={
                    "provider_thread_id": "thread_123",
                    "business_id": target.business_id,
                    "environment": target.environment,
                },
            )
        ),
        contacts=contacts,
        conversations=conversations,
        sequence_service=sequence,
        message_repository=messages,
    )

    result = service.handle_textgrid_webhook({}, signature=None)

    assert result["status"] == "processed"
    assert result["action"] == "stop"
    assert sequence.stop_calls == [target.phone]
    assert sequence.pause_calls == []
    assert messages.calls == [(target.id, "thread_123")]
    tasks = TasksRepository(client).list()
    assert tasks == []


def test_inbound_sms_fallback_does_not_rebind_existing_conversation_thread_id() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    conversations = ConversationsRepository(client)
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+155****4567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )
    existing = conversations.get_or_create(
        business_id=lead.business_id,
        environment=lead.environment,
        contact_id=lead.id,
        channel="sms",
        provider_thread_id="thread_existing",
    )

    class _RecordingMessageRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str | None]] = []

        def append_inbound_message(self, event: NormalizedSmsEvent, *, lead, provider_thread_id=None) -> None:
            self.calls.append((lead.id, provider_thread_id))

    messages = _RecordingMessageRepository()
    sequence = _StubSequenceService()
    service = InboundSmsService(
        textgrid_adapter=_StubTextgridAdapter(
            event=NormalizedSmsEvent(
                event_type="inbound",
                body="stop",
                from_number=lead.phone,
                to_number="+134****6666",
                external_id="sms_thread_fallback_1",
                metadata={
                    "provider_thread_id": "thread_incoming",
                    "business_id": lead.business_id,
                    "environment": lead.environment,
                },
            )
        ),
        contacts=contacts,
        conversations=conversations,
        sequence_service=sequence,
        message_repository=messages,
    )

    result = service.handle_textgrid_webhook({}, signature=None)

    assert result["status"] == "processed"
    assert result["action"] == "stop"
    assert messages.calls == [(lead.id, None)]
    current = conversations.find_by_provider_thread(
        business_id=lead.business_id,
        environment=lead.environment,
        channel="sms",
        provider_thread_id="thread_existing",
    )
    assert current is not None
    assert current.provider_thread_id == existing.provider_thread_id


def test_inbound_sms_handles_a_raw_textgrid_payload_end_to_end() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    conversations = ConversationsRepository(client)
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+155****4567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )
    conversations.get_or_create(
        business_id=lead.business_id,
        environment=lead.environment,
        contact_id=lead.id,
        channel="sms",
        provider_thread_id="thread_123",
    )

    messages = _StubMessageRepository()
    sequence = _StubSequenceService()
    service = InboundSmsService(
        settings=Settings(textgrid_webhook_secret="whsec_123"),
        contacts=contacts,
        conversations=conversations,
        sequence_service=sequence,
        message_repository=messages,
    )
    payload = {
        "From": lead.phone,
        "To": "+134****6666",
        "Body": "stop",
        "MessageSid": "SM200",
        "Metadata": {
            "provider_thread_id": "thread_123",
            "business_id": lead.business_id,
            "environment": lead.environment,
        },
    }
    signature = _twilio_style_signature("whsec_123", "https://runtime.example.com/marketing/webhooks/textgrid", payload)

    result = service.handle_textgrid_webhook(
        payload,
        signature=signature,
        request_url="https://runtime.example.com/marketing/webhooks/textgrid",
    )

    assert result["status"] == "processed"
    assert result["action"] == "stop"
    assert sequence.stop_calls == [lead.phone]
    assert messages.calls == [(lead.id, "thread_123")]


def test_inbound_sms_without_tenant_metadata_skips_unscoped_provider_thread_lookup() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    conversations = _NoGlobalProviderThreadRepository()
    service = InboundSmsService(
        textgrid_adapter=_StubTextgridAdapter(
            event=NormalizedSmsEvent(
                event_type="inbound",
                body="stop",
                from_number="+155****0000",
                to_number="+134****6666",
                external_id="sms_thread_unscoped_1",
                metadata={"provider_thread_id": "thread_123"},
            )
        ),
        contacts=contacts,
        conversations=conversations,
    )

    result = service.handle_textgrid_webhook({}, signature=None)

    assert result["status"] == "processed"
    assert result["action"] == "stop"
    assert conversations.global_calls == []
    tasks = TasksRepository(client).list()
    assert len(tasks) == 1
    assert tasks[0].task_type.value == "manual_review"


def test_textgrid_normalize_incoming_webhook_preserves_tenant_metadata() -> None:
    normalized = normalize_incoming_webhook(
        {
            "From": "+155****4567",
            "To": "+134****5914",
            "Body": "stop",
            "provider_thread_id": "thread_123",
            "business_id": "limitless",
            "environment": "dev",
        }
    )

    assert normalized["type"] == "message.inbound"
    assert normalized["metadata"]["provider"] == "textgrid"
    assert normalized["metadata"]["provider_thread_id"] == "thread_123"
    assert normalized["metadata"]["business_id"] == "limitless"
    assert normalized["metadata"]["environment"] == "dev"