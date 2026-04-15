from app.db.bookings import BookingsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.contacts import ContactsRepository
from app.db.conversations import ConversationsRepository
from app.core.config import Settings
from app.db.messages import MessagesRepository
from app.db.sequences import SequencesRepository
from app.db.tasks import TasksRepository
from app.models.marketing_leads import LeadUpsertRequest
from app.models.messages import MessageDirection, MessageStatus
from app.models.sequences import SequenceEnrollmentStatus


def build_repositories() -> tuple[
    ContactsRepository,
    ConversationsRepository,
    MessagesRepository,
    BookingsRepository,
    TasksRepository,
    SequencesRepository,
]:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return (
        ContactsRepository(client),
        ConversationsRepository(client),
        MessagesRepository(client),
        BookingsRepository(client),
        TasksRepository(client),
        SequencesRepository(client),
    )


def test_marketing_repositories_cover_live_marketing_flow() -> None:
    contacts, conversations, messages, bookings, tasks, sequences = build_repositories()

    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Martin",
            phone="+18325550111",
            email="martin@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    deduped = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Martin",
            phone="+18325550111",
            email="updated@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    assert lead.id == deduped.id
    assert deduped.email == "updated@example.com"

    conversation = conversations.get_or_create(
        business_id="limitless",
        environment="dev",
        contact_id=lead.id,
        channel="sms",
    )
    same_conversation = conversations.get_or_create(
        business_id="limitless",
        environment="dev",
        contact_id=lead.id,
        channel="sms",
    )
    other_tenant_conversation = conversations.get_or_create(
        business_id="limitless",
        environment="prod",
        contact_id=lead.id,
        channel="sms",
    )

    assert conversation.provider_thread_id == same_conversation.provider_thread_id
    assert (
        other_tenant_conversation.provider_thread_id
        != conversation.provider_thread_id
    )

    outbound = messages.append_outbound(
        business_id="limitless",
        environment="dev",
        contact_id=lead.id,
        conversation_id=conversation.provider_thread_id,
        channel="sms",
        provider="textgrid",
        body="Thanks for submitting. Here's your booking link.",
    )
    inbound = messages.append_inbound(
        business_id="limitless",
        environment="dev",
        contact_id=lead.id,
        conversation_id=conversation.provider_thread_id,
        channel="sms",
        provider="textgrid",
        body="Booked for tomorrow morning.",
    )

    assert outbound.direction == MessageDirection.OUTBOUND
    assert outbound.status == MessageStatus.QUEUED
    assert inbound.direction == MessageDirection.INBOUND
    assert inbound.status == MessageStatus.RECEIVED

    booking_event = bookings.append_event(
        business_id="limitless",
        environment="dev",
        contact_id=lead.id,
        conversation_id=conversation.provider_thread_id,
        event_type="booked",
        provider="calcom",
        external_booking_id="booking_123",
        metadata={"start_time": "2026-04-15T14:00:00Z"},
    )
    assert booking_event.event_type == "booked"

    manual_call = tasks.create_manual_call(
        business_id="limitless",
        environment="dev",
        contact_id=lead.id,
        title="Call lead after high-intent SMS reply",
    )
    assert manual_call.status == "open"

    enrollment = sequences.create(
        business_id="limitless",
        environment="dev",
        contact_id=lead.id,
        sequence_key="lease_option_non_booker_v1",
    )
    paused = sequences.pause(
        enrollment.id,
        business_id="limitless",
        environment="dev",
    )
    completed = sequences.complete(
        enrollment.id,
        business_id="limitless",
        environment="dev",
    )

    assert paused is not None
    assert completed is not None
    assert paused.status == SequenceEnrollmentStatus.PAUSED
    assert completed.status == SequenceEnrollmentStatus.COMPLETED


def test_marketing_repositories_can_translate_through_supabase_adapters(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        marketing_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )

    from app.db import contacts as contacts_module
    from app.db import conversations as conversations_module

    def fake_resolve_tenant(business_id: str, environment: str, *, settings=None):
        class Tenant:
            business_pk = 7
            environment = "dev"

        return Tenant()

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        if table == "contacts" and params.get("phone") == "eq.+18325550111":
            return []
        if table == "contacts" and params.get("external_contact_id") == "eq.ctc_101":
            return [{"id": 101}]
        if table == "conversations":
            return []
        return []

    inserted_rows = {"contacts": [], "conversations": []}

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        inserted_rows[table].append(rows[0])
        if table == "contacts":
            return [{"id": 101, "external_contact_id": "pending", "name": "Martin", "email": "martin@example.com", "phone": "+18325550111", "metadata": {"property_address": "123 Main St, Houston, TX", "booking_status": "pending"}, "created_at": "2026-04-14T00:00:00Z", "updated_at": "2026-04-14T00:00:00Z"}]
        if table == "conversations":
            return [{"external_conversation_id": "cnv_201", "status": "open"}]
        raise AssertionError(table)

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        assert table == "contacts"
        return [{"id": 101, "external_contact_id": "ctc_101", "name": "Martin", "email": "martin@example.com", "phone": "+18325550111", "metadata": {"property_address": "123 Main St, Houston, TX", "booking_status": "pending"}, "created_at": "2026-04-14T00:00:00Z", "updated_at": "2026-04-14T00:00:00Z"}]

    monkeypatch.setattr(contacts_module, "resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr(contacts_module, "fetch_rows", fake_fetch_rows)
    monkeypatch.setattr(contacts_module, "insert_rows", fake_insert_rows)
    monkeypatch.setattr(contacts_module, "patch_rows", fake_patch_rows)
    monkeypatch.setattr(conversations_module, "resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr(conversations_module, "fetch_rows", fake_fetch_rows)
    monkeypatch.setattr(conversations_module, "insert_rows", fake_insert_rows)

    contacts = ContactsRepository(settings=settings)
    conversations = ConversationsRepository(settings=settings)

    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Martin",
            phone="+18325550111",
            email="martin@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )
    conversation = conversations.get_or_create(
        business_id="limitless",
        environment="dev",
        contact_id=lead.id,
        channel="sms",
    )

    assert lead.id == "ctc_101"
    assert inserted_rows["contacts"][0]["business_id"] == 7
    assert conversation.provider_thread_id == "cnv_201"
