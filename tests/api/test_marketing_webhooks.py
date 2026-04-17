from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.contacts import ContactsRepository
from app.db.tasks import TasksRepository
from app.main import app
from app.services.booking_service import BookingService, ManualCallTaskRequest, NormalizedBookingEvent
from app.services.inbound_sms_service import InboundSmsService, LeaseOptionSequenceStepRequest, NormalizedSmsEvent
from app.services.marketing_lead_service import LeadIntakePayload, MarketingLeadService
from app.models.marketing_leads import LeadUpsertRequest

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_post_calcom_webhook_processes_booking_event(monkeypatch) -> None:
    class StubBookingService:
        def __init__(self) -> None:
            self.calls = []

        def handle_calcom_webhook(self, payload, *, signature):
            self.calls.append((payload, signature))
            return {"status": "processed", "lead_id": "lead_123", "booking_status": "booked"}

    from app.api import marketing as marketing_api

    stub = StubBookingService()
    monkeypatch.setattr(marketing_api, "booking_service", stub)
    client = TestClient(app)

    response = client.post(
        "/marketing/webhooks/calcom",
        json={"event": "BOOKING_CREATED", "payload": {"metadata": {"lead_id": "lead_123"}}},
        headers={**AUTH_HEADERS, "x-cal-signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "processed", "lead_id": "lead_123", "booking_status": "booked"}
    assert len(stub.calls) == 1


def test_post_textgrid_webhook_processes_inbound_sms(monkeypatch) -> None:
    class StubInboundSmsService:
        def __init__(self) -> None:
            self.calls = []

        def handle_textgrid_webhook(self, payload, *, signature):
            self.calls.append((payload, signature))
            return {"status": "processed", "event_type": "inbound_message", "action": "qualify"}

    from app.api import marketing as marketing_api

    stub = StubInboundSmsService()
    monkeypatch.setattr(marketing_api, "inbound_sms_service", stub)
    client = TestClient(app)

    response = client.post(
        "/marketing/webhooks/textgrid",
        json={"From": "+15557654321", "To": "+15551234567", "Body": "Yes, still interested"},
        headers={**AUTH_HEADERS, "x-textgrid-signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "processed", "event_type": "inbound_message", "action": "qualify"}
    assert len(stub.calls) == 1


def test_post_non_booker_check_runs_internal_check(monkeypatch) -> None:
    class StubBookingService:
        def __init__(self) -> None:
            self.calls = []

        def run_non_booker_check(self, request):
            self.calls.append(request)
            return {
                "booking_status": "pending",
                "should_enroll_in_sequence": True,
                "start_day": 0,
            }

    from app.api import marketing as marketing_api

    stub = StubBookingService()
    monkeypatch.setattr(marketing_api, "booking_service", stub)
    client = TestClient(app)

    response = client.post(
        "/marketing/internal/non-booker-check",
        json={"leadId": "lead_123", "businessId": "limitless", "environment": "dev"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "bookingStatus": "pending",
        "shouldEnrollInSequence": True,
        "startDay": 0,
    }
    assert len(stub.calls) == 1


def test_booking_service_rejects_invalid_calcom_signature() -> None:
    service = BookingService(settings=Settings(cal_webhook_secret="cal_whsec_1"))

    try:
        service.handle_calcom_webhook(
            {
                "triggerEvent": "BOOKING_CREATED",
                "payload": {"booking": {"uid": "book_1", "metadata": {"lead_id": "lead_1"}}},
            },
            signature="sha256=bad",
            raw_body=b"{}",
        )
    except ValueError as exc:
        assert str(exc) == "Invalid Cal.com webhook signature"
    else:
        raise AssertionError("Expected invalid signature to raise")


def test_inbound_sms_service_rejects_invalid_textgrid_signature() -> None:
    service = InboundSmsService(settings=Settings(textgrid_webhook_secret="whsec_1"))

    try:
        service.handle_textgrid_webhook(
            {"From": "+15551234567", "To": "+15557654321", "Body": "stop"},
            signature="invalid",
            request_url="https://runtime.example.com/marketing/webhooks/textgrid",
        )
    except ValueError as exc:
        assert str(exc) == "Invalid TextGrid webhook signature"
    else:
        raise AssertionError("Expected invalid signature to raise")


def test_sequence_step_and_manual_call_task_use_live_repositories() -> None:
    class StubRequestSender:
        def __init__(self) -> None:
            self.calls = []

        def __call__(self, payload):
            self.calls.append(payload)

    sender = StubRequestSender()
    lead_service = MarketingLeadService(
        settings=Settings(
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="+13467725914",
            textgrid_sms_url="https://api.textgrid.com/custom/messages",
        ),
        request_sender=sender,
    )
    result = lead_service.intake_lead(
        LeadIntakePayload(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    sms_service = InboundSmsService(
        settings=Settings(
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="+13467725914",
            textgrid_sms_url="https://api.textgrid.com/custom/messages",
        ),
        request_sender=sender,
    )
    step = sms_service.dispatch_lease_option_sequence_step(
        LeaseOptionSequenceStepRequest(
            lead_id=result["lead_id"],
            business_id="limitless",
            environment="dev",
            day=1,
            channel="sms",
            template_id="lease_option_day_2_sms",
        )
    )
    task = BookingService().create_manual_call_task(
        ManualCallTaskRequest(
            lead_id=result["lead_id"],
            business_id="limitless",
            environment="dev",
            sequence_day=1,
            reason="lease_option_sequence_checkpoint",
        )
    )

    assert step["status"] == "queued"
    assert len(sender.calls) >= 2
    stored_task = TasksRepository().client.store.marketing_task_rows[task["task_id"]]
    assert stored_task.title.startswith("Call lead:")


def test_booking_service_duplicate_webhook_does_not_repeat_sequence_suppression() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    lead = ContactsRepository(client).upsert_lead(
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
        def __init__(self) -> None:
            self.suppressed = 0

        def suppress_for_booked_lead(self, *, lead_id: str) -> None:
            self.suppressed += 1

        def enroll_non_booker(self, *, lead_id: str, business_id: str, environment: str) -> None:
            return None

    sequence_service = StubSequenceService()
    service = BookingService(
        calcom_adapter=StubCalcomAdapter(),
        sequence_service=sequence_service,
        contacts=ContactsRepository(client),
    )

    first = service.handle_calcom_webhook({}, signature=None)
    second = service.handle_calcom_webhook({}, signature=None)

    assert first["status"] == "processed"
    assert second["status"] == "processed"
    assert sequence_service.suppressed == 1


def test_inbound_sms_duplicate_webhook_does_not_repeat_side_effects() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    lead = ContactsRepository(client).upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    class StubTextgridAdapter:
        def verify_signature(self, payload, *, signature, request_url=None):
            return True

        def normalize(self, payload):
            return NormalizedSmsEvent(
                event_type="inbound",
                body="stop",
                from_number=lead.phone,
                to_number="+13467725914",
                external_id="sms_123",
            )

    class StubMessageRepository:
        def __init__(self) -> None:
            self.calls = 0

        def append_inbound_message(self, event: NormalizedSmsEvent) -> None:
            self.calls += 1

    class StubSequenceService:
        def __init__(self) -> None:
            self.stop_calls = 0

        def stop(self, *, phone_number: str) -> None:
            self.stop_calls += 1

        def pause(self, *, phone_number: str) -> None:
            return None

    messages = StubMessageRepository()
    sequence = StubSequenceService()
    service = InboundSmsService(
        textgrid_adapter=StubTextgridAdapter(),
        message_repository=messages,
        sequence_service=sequence,
        contacts=ContactsRepository(client),
    )

    first = service.handle_textgrid_webhook({}, signature=None)
    second = service.handle_textgrid_webhook({}, signature=None)

    assert first["status"] == "processed"
    assert second["status"] == "processed"
    assert messages.calls == 1
    assert sequence.stop_calls == 1


def test_sequence_step_calls_message_logging_hook_after_dispatch() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    lead = ContactsRepository(client).upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    class StubRequestSender:
        def __call__(self, payload):
            return None

    class StubMessageLoggingHook:
        def __init__(self) -> None:
            self.calls = []

        def log_sequence_dispatch(self, *, lead_id, channel, body, provider):
            self.calls.append((lead_id, channel, body, provider))

    hook = StubMessageLoggingHook()
    service = InboundSmsService(
        settings=Settings(
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="+13467725914",
            textgrid_sms_url="https://api.textgrid.com/custom/messages",
        ),
        request_sender=StubRequestSender(),
        message_logging_hook=hook,
        contacts=ContactsRepository(client),
    )

    result = service.dispatch_lease_option_sequence_step(
        LeaseOptionSequenceStepRequest(
            lead_id=lead.id,
            business_id="limitless",
            environment="dev",
            day=1,
            channel="sms",
            template_id="lease_option_day_2_sms",
        )
    )

    assert result["status"] == "queued"
    assert len(hook.calls) == 1
    assert hook.calls[0][0] == lead.id
