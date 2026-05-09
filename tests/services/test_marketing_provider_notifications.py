import json
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.contacts import ContactsRepository
from app.models.marketing_leads import LeadUpsertRequest
from app.providers.textgrid import build_outbound_sms_request
from app.services.booking_service import (
    BookingService,
    NormalizedBookingEvent,
    _MarketingBookingStateRepository,
    _TriggerAppointmentReminderScheduler,
)
from app.services.marketing_lead_service import LeadIntakePayload, MarketingLeadService


def test_textgrid_outbound_request_normalizes_us_numbers_to_e164() -> None:
    request = build_outbound_sms_request(
        account_sid="acct_123",
        auth_token="token_123",
        from_number="3462891390",
        to_number="5551234567",
        body="Test",
    )

    assert request["payload"]["From"] == "+13462891390"
    assert request["payload"]["To"] == "+15551234567"


def test_lead_intake_sends_confirmation_sms_email_and_slack_with_booking_link() -> None:
    sent_requests: list[dict[str, object]] = []
    sent_email: list[dict[str, object]] = []

    class StubLeadRepository:
        def upsert_lead(self, payload: LeadIntakePayload) -> str:
            return "lead_speed_123"

    def request_sender(outbound_request):
        sent_requests.append(outbound_request)
        endpoint = str(outbound_request["endpoint"])
        if "slack.com" in endpoint:
            return {"ok": True, "channel": "CINTAKE", "ts": "171234.567"}
        return {"sid": "SM_SPEED_123"}

    def resend_sender(settings, *, to: str, subject: str, text: str, html=None):
        sent_email.append({"to": to, "subject": subject, "text": text, "html": html})
        return {"provider_message_id": "email_speed_123"}

    service = MarketingLeadService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="3462891390",
            resend_api_key="re_123",
            resend_from_email="Martin at Limitless <martin@example.com>",
            resend_reply_to_email="martin@example.com",
            slack_bot_token="xoxb-test",
            slack_channel_intake="CINTAKE",
            cal_booking_url="https://cal.com/limitless/lease-option-review",
        ),
        lead_repository=StubLeadRepository(),
        request_sender=request_sender,
        resend_email_sender=resend_sender,
    )

    result = service.intake_lead(
        LeadIntakePayload(
            business_id="limitless",
            environment="prod",
            first_name="Maya",
            last_name="Seller",
            phone="5551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
            timeline_to_sell="ASAP",
            asking_price_goal="$350,000",
            seller_goal="Need speed to lead",
            sms_consent=True,
            utm_source="google",
            lp_var="houston-v1",
        )
    )

    booking_url = result["booking_url"]
    assert parse_qs(urlparse(booking_url).query)["lead_id"] == ["lead_speed_123"]
    assert [effect["name"] for effect in result["side_effects"]] == [
        "confirmation_sms",
        "confirmation_email",
        "operator_slack_notification",
        "trigger_non_booker_check",
    ]
    assert result["side_effects"][0]["status"] == "queued"
    assert result["side_effects"][1]["status"] == "queued"
    assert result["side_effects"][2]["status"] == "queued"

    sms_request = sent_requests[0]
    assert sms_request["payload"]["To"] == "+15551234567"
    assert sms_request["payload"]["From"] == "+13462891390"
    assert booking_url in sms_request["payload"]["Body"]
    assert "Reply STOP to opt out" in sms_request["payload"]["Body"]

    assert sent_email == [
        {
            "to": "maya@example.com",
            "subject": "Your lease-option review call",
            "text": sms_request["payload"]["Body"],
            "html": None,
        }
    ]

    slack_request = sent_requests[1]
    assert slack_request["endpoint"] == "https://slack.com/api/chat.postMessage"
    assert slack_request["headers"]["Authorization"] == "Bearer xoxb-test"
    assert slack_request["payload"]["channel"] == "CINTAKE"
    assert "New lease-option lead: Maya Seller" in slack_request["payload"]["text"]
    assert "123 Main St" in json.dumps(slack_request["payload"])


def test_lead_intake_skips_slack_when_live_sends_are_disabled_even_if_configured() -> None:
    class StubLeadRepository:
        def upsert_lead(self, payload: LeadIntakePayload) -> str:
            return "lead_safe_123"

    def request_sender(_outbound_request):
        raise AssertionError("Slack/TextGrid requests should not be sent when live sends are disabled")

    def resend_sender(*_args, **_kwargs):
        raise AssertionError("Resend requests should not be sent when live sends are disabled")

    service = MarketingLeadService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=False,
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="3462891390",
            resend_api_key="re_123",
            resend_from_email="Martin at Limitless <martin@example.com>",
            slack_bot_token="xoxb-test",
            slack_channel_intake="CINTAKE",
            cal_booking_url="https://cal.com/limitless/lease-option-review",
        ),
        lead_repository=StubLeadRepository(),
        request_sender=request_sender,
        resend_email_sender=resend_sender,
    )

    result = service.intake_lead(
        LeadIntakePayload(
            business_id="limitless",
            environment="prod",
            first_name="Maya",
            phone="5551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
            sms_consent=True,
        )
    )

    side_effects = {effect["name"]: effect["status"] for effect in result["side_effects"]}
    assert side_effects["confirmation_sms"] == "skipped"
    assert side_effects["confirmation_email"] == "skipped"
    assert side_effects["operator_slack_notification"] == "skipped"


def test_booking_service_schedules_appointment_reminders_when_calcom_booking_is_created() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="prod",
            first_name="Maya",
            phone="5551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
            sms_consent=True,
        )
    )

    class StubCalcomAdapter:
        def normalize(self, payload, *, signature, raw_body=None):
            return NormalizedBookingEvent(
                lead_id=lead.id,
                booking_status="booked",
                event_name="booking.created",
                external_booking_id="book_123",
                starts_at="2026-05-12T16:00:00Z",
            )

    class StubAppointmentNotifier:
        def send_appointment_confirmation(self, *, lead_id: str):
            return {"sms": "SM_BOOKED", "email": "email_booked"}

        def send_appointment_reminder(self, *, lead_id: str, reminder_label: str, starts_at: str | None = None):
            return {"sms": f"SM_REMINDER_{reminder_label}", "email": f"email_reminder_{reminder_label}"}

    class StubSequenceService:
        def suppress_for_booked_lead(self, *, lead_id: str) -> None:
            return None

        def enroll_non_booker(self, *, lead_id: str, business_id: str, environment: str) -> None:
            return None

    class StubReminderScheduler:
        def __init__(self) -> None:
            self.calls = []

        def schedule_appointment_reminders(self, *, lead, event):
            self.calls.append((lead, event))
            return [
                {"name": "appointment_reminder_24h", "status": "scheduled", "delay": "86400s"},
                {"name": "appointment_reminder_1h", "status": "scheduled", "delay": "3600s"},
            ]

    scheduler = StubReminderScheduler()
    service = BookingService(
        calcom_adapter=StubCalcomAdapter(),
        booking_repository=_MarketingBookingStateRepository(contacts=contacts),
        appointment_notifier=StubAppointmentNotifier(),
        appointment_reminder_scheduler=scheduler,
        sequence_service=StubSequenceService(),
        contacts=contacts,
    )

    result = service.handle_calcom_webhook({}, signature=None)

    assert result == {"status": "processed", "lead_id": lead.id, "booking_status": "booked"}
    assert len(scheduler.calls) == 1
    assert scheduler.calls[0][0].id == lead.id
    assert scheduler.calls[0][1].starts_at == "2026-05-12T16:00:00Z"


def test_trigger_appointment_reminder_scheduler_posts_delayed_reminder_jobs(monkeypatch) -> None:
    from app.services import booking_service as booking_service_module

    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="prod",
            first_name="Maya",
            phone="5551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
            sms_consent=True,
        )
    )
    event = NormalizedBookingEvent(
        lead_id=lead.id,
        booking_status="booked",
        event_name="booking.created",
        external_booking_id="book_123",
        starts_at="2026-05-12T16:00:00Z",
    )
    captured: list[dict[str, object]] = []

    class StubResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    def fake_urlopen(request, timeout: int):
        captured.append(
            {
                "url": request.full_url,
                "method": request.get_method(),
                "headers": {key.lower(): value for key, value in request.header_items()},
                "body": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return StubResponse()

    monkeypatch.setattr(booking_service_module.http_request, "urlopen", fake_urlopen)
    scheduler = _TriggerAppointmentReminderScheduler(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            marketing_appointment_reminders_enabled=True,
            trigger_secret_key="tr_dev_123",
            trigger_api_url="https://api.trigger.dev",
            trigger_appointment_reminder_task_id="marketing-send-appointment-reminder",
        ),
        now_fn=lambda: datetime(2026, 5, 11, 15, 0, tzinfo=UTC),
    )

    result = scheduler.schedule_appointment_reminders(lead=lead, event=event)

    assert result == [
        {"name": "appointment_reminder_24h", "status": "scheduled", "delay": "3600s"},
        {"name": "appointment_reminder_1h", "status": "scheduled", "delay": "86400s"},
    ]
    assert [call["url"] for call in captured] == [
        "https://api.trigger.dev/api/v1/tasks/marketing-send-appointment-reminder/trigger",
        "https://api.trigger.dev/api/v1/tasks/marketing-send-appointment-reminder/trigger",
    ]
    assert [call["body"]["payload"]["reminderLabel"] for call in captured] == ["24h", "1h"]
    assert [call["body"]["options"]["delay"] for call in captured] == ["3600s", "86400s"]
    assert captured[0]["headers"]["authorization"] == "Bearer tr_dev_123"


def test_booking_service_dispatches_appointment_reminder_through_configured_notifier() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="prod",
            first_name="Maya",
            phone="5551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
            sms_consent=True,
        )
    )
    contacts.update_booking_status(lead.id, "booked")

    class StubAppointmentNotifier:
        def __init__(self) -> None:
            self.calls = []

        def send_appointment_confirmation(self, *, lead_id: str):
            return {}

        def send_appointment_reminder(self, *, lead_id: str, reminder_label: str, starts_at: str | None = None):
            self.calls.append((lead_id, reminder_label, starts_at))
            return {"sms": "SM_1H", "email": "email_1h"}

    notifier = StubAppointmentNotifier()
    service = BookingService(appointment_notifier=notifier, contacts=contacts)

    result = service.send_appointment_reminder(
        lead_id=lead.id,
        business_id="limitless",
        environment="prod",
        reminder_label="1h",
        starts_at="2026-05-12T16:00:00Z",
    )

    assert result == {
        "lead_id": lead.id,
        "status": "queued",
        "sms_provider_message_id": "SM_1H",
        "email_provider_message_id": "email_1h",
    }
    assert notifier.calls == [(lead.id, "1h", "2026-05-12T16:00:00Z")]
