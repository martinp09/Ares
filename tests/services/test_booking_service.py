from app.db.bookings import BookingsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.contacts import ContactsRepository
from app.db.sequences import SequencesRepository
from app.core.config import Settings
from app.db.opportunities import OpportunitiesRepository
from app.models.marketing_leads import LeadUpsertRequest
from app.models.opportunities import OpportunitySourceLane, OpportunityStage
from app.services.booking_service import (
    BookingService,
    LeaseOptionSequenceGuardRequest,
    NormalizedBookingEvent,
    _MarketingBookingStateRepository,
)
from app.services.opportunity_service import OpportunityService


def test_booked_calcom_event_creates_lease_option_opportunity() -> None:
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

    class StubCalcomAdapter:
        def normalize(self, payload, *, signature, raw_body=None):
            return NormalizedBookingEvent(
                lead_id=lead.id,
                booking_status="booked",
                event_name="booking.created",
                external_booking_id="book_123",
            )

    class StubSequenceService:
        def suppress_for_booked_lead(self, *, lead_id: str) -> None:
            return None

        def enroll_non_booker(self, *, lead_id: str, business_id: str, environment: str) -> None:
            return None

    class StubAppointmentNotifier:
        def send_appointment_confirmation(self, *, lead_id: str) -> None:
            return None

    class StubWebhookReceipts:
        def record_calcom_event(self, *, event, lead, payload):
            return None, False

        def mark_processed(self, receipt_id: str | None) -> None:
            return None

    service = BookingService(
        calcom_adapter=StubCalcomAdapter(),
        booking_repository=_MarketingBookingStateRepository(
            contacts=contacts,
            bookings=BookingsRepository(client),
        ),
        appointment_notifier=StubAppointmentNotifier(),
        sequence_service=StubSequenceService(),
        contacts=contacts,
        webhook_receipts=StubWebhookReceipts(),
        opportunity_service=OpportunityService(OpportunitiesRepository(client)),
    )

    result = service.handle_calcom_webhook({}, signature=None)
    opportunities = OpportunitiesRepository(client).list(business_id="limitless", environment="dev")

    assert result == {"status": "processed", "lead_id": lead.id, "booking_status": "booked"}
    assert len(opportunities) == 1
    assert opportunities[0].contact_id == lead.id
    assert opportunities[0].source_lane == OpportunitySourceLane.LEASE_OPTION_INBOUND
    assert opportunities[0].stage == OpportunityStage.QUALIFIED_OPPORTUNITY
    assert opportunities[0].metadata == {
        "booking_status": "booked",
        "event_name": "booking.created",
    }


def test_sequence_guard_uses_latest_sequence_state_for_pending_leads() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    sequences = SequencesRepository(client)
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
    enrollment = sequences.create(
        business_id=lead.business_id,
        environment=lead.environment,
        contact_id=lead.id,
        sequence_key="lease_option_non_booker_v1",
    )
    sequences.pause(
        enrollment.id,
        business_id=lead.business_id,
        environment=lead.environment,
    )

    service = BookingService(
        booking_repository=_MarketingBookingStateRepository(
            contacts=contacts,
            bookings=BookingsRepository(client),
        ),
        contacts=contacts,
    )
    result = service.get_lease_option_sequence_guard(
        LeaseOptionSequenceGuardRequest(
            lead_id=lead.id,
            business_id=lead.business_id,
            environment=lead.environment,
            day=2,
        )
    )

    assert result["booking_status"] == "pending"
    assert result["sequence_status"] == "paused"
    assert result["opted_out"] is False


def test_booked_calcom_event_logs_outbound_confirmation_messages() -> None:
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

    class StubCalcomAdapter:
        def normalize(self, payload, *, signature, raw_body=None):
            return NormalizedBookingEvent(
                lead_id=lead.id,
                booking_status="booked",
                event_name="booking.created",
                external_booking_id="book_456",
            )

    class StubSequenceService:
        def suppress_for_booked_lead(self, *, lead_id: str) -> None:
            return None

        def enroll_non_booker(self, *, lead_id: str, business_id: str, environment: str) -> None:
            return None

    class StubAppointmentNotifier:
        def send_appointment_confirmation(self, *, lead_id: str) -> None:
            return None

    service = BookingService(
        settings=Settings(
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="+13467725914",
            resend_api_key="resend_123",
            resend_from_email="ops@example.com",
        ),
        calcom_adapter=StubCalcomAdapter(),
        booking_repository=_MarketingBookingStateRepository(
            contacts=contacts,
            bookings=BookingsRepository(client),
        ),
        appointment_notifier=StubAppointmentNotifier(),
        sequence_service=StubSequenceService(),
        contacts=contacts,
    )

    service.handle_calcom_webhook({}, signature=None)

    message_rows = getattr(client.store, "marketing_message_rows", {})
    assert len(message_rows) == 2
