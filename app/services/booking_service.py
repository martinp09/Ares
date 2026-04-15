from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol
from urllib import request as http_request

from app.core.config import Settings, get_settings
from app.db.bookings import BookingsRepository
from app.db.contacts import ContactsRepository
from app.db.sequences import SequencesRepository
from app.db.tasks import TasksRepository
from app.providers.calcom import normalize_booking_webhook, verify_webhook_signature
from app.providers.resend import build_send_email_request
from app.providers.textgrid import build_outbound_sms_request


BookingStatus = Literal["pending", "booked", "rescheduled", "cancelled"]
SequenceStatus = Literal["active", "paused", "completed", "stopped"]
LEASE_OPTION_SEQUENCE_KEY = "lease_option_non_booker_v1"


@dataclass(slots=True)
class NonBookerCheckRequest:
    lead_id: str
    business_id: str
    environment: str


@dataclass(slots=True)
class LeaseOptionSequenceGuardRequest:
    lead_id: str
    business_id: str
    environment: str
    day: int


@dataclass(slots=True)
class ManualCallTaskRequest:
    lead_id: str
    business_id: str
    environment: str
    sequence_day: int
    reason: str


@dataclass(slots=True)
class NormalizedBookingEvent:
    lead_id: str
    booking_status: BookingStatus
    event_name: str
    provider: str = "cal.com"
    external_booking_id: str | None = None
    metadata: dict[str, object] | None = None


class CalcomWebhookAdapter(Protocol):
    def normalize(
        self,
        payload: dict[str, Any],
        *,
        signature: str | None,
        raw_body: bytes | None = None,
    ) -> NormalizedBookingEvent: ...


class BookingStateRepository(Protocol):
    def apply_booking_event(self, event: NormalizedBookingEvent) -> bool: ...

    def get_booking_status(self, lead_id: str) -> BookingStatus: ...


class AppointmentNotifier(Protocol):
    def send_appointment_confirmation(self, *, lead_id: str) -> None: ...


class SequenceEnrollmentService(Protocol):
    def suppress_for_booked_lead(self, *, lead_id: str) -> None: ...

    def enroll_non_booker(self, *, lead_id: str, business_id: str, environment: str) -> None: ...


class _DefaultCalcomWebhookAdapter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def normalize(
        self,
        payload: dict[str, Any],
        *,
        signature: str | None,
        raw_body: bytes | None = None,
    ) -> NormalizedBookingEvent:
        if self.settings.cal_webhook_secret:
            if raw_body is None or not verify_webhook_signature(self.settings.cal_webhook_secret, signature, raw_body):
                raise ValueError("Invalid Cal.com webhook signature")
        normalized = normalize_booking_webhook(payload)
        lead_id = str(normalized.get("lead_id") or "").strip()
        if not lead_id:
            raise ValueError("Missing lead_id in Cal.com webhook payload")
        booking_status = str(normalized["booking_status"])
        if booking_status not in {"booked", "rescheduled", "cancelled"}:
            booking_status = "pending"
        return NormalizedBookingEvent(
            lead_id=lead_id,
            booking_status=booking_status,  # type: ignore[arg-type]
            event_name=str(normalized["event_type"]),
            external_booking_id=(
                None if normalized.get("external_booking_id") is None else str(normalized["external_booking_id"])
            ),
            metadata=dict(normalized.get("metadata") or {}),
        )


class _MarketingBookingStateRepository:
    def __init__(
        self,
        *,
        contacts: ContactsRepository | None = None,
        bookings: BookingsRepository | None = None,
    ) -> None:
        self.contacts = contacts or ContactsRepository()
        self.bookings = bookings or BookingsRepository()

    def apply_booking_event(self, event: NormalizedBookingEvent) -> bool:
        lead = self.contacts.get_lead(event.lead_id)
        previous_status = lead.booking_status if lead is not None else "pending"
        updated = self.contacts.update_booking_status(event.lead_id, event.booking_status)
        if updated is not None:
            self.bookings.append_event(
                business_id=updated.business_id,
                environment=updated.environment,
                contact_id=updated.id,
                conversation_id=None,
                event_type=event.booking_status,
                provider=event.provider,
                external_booking_id=event.external_booking_id,
                metadata=event.metadata or {},
            )
        return previous_status != "booked" and event.booking_status == "booked"

    def get_booking_status(self, lead_id: str) -> BookingStatus:
        lead = self.contacts.get_lead(lead_id)
        if lead is None:
            return "pending"
        return lead.booking_status


class _NoopAppointmentNotifier:
    def send_appointment_confirmation(self, *, lead_id: str) -> None:
        return None


class _ConfiguredAppointmentNotifier:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        contacts: ContactsRepository | None = None,
        request_sender: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.contacts = contacts or ContactsRepository()
        self.request_sender = request_sender or _default_request_sender

    def send_appointment_confirmation(self, *, lead_id: str) -> None:
        lead = self.contacts.get_lead(lead_id)
        if lead is None:
            return
        message = f"Thanks {lead.first_name}, your lease-option appointment is confirmed."
        if (
            self.settings.textgrid_account_sid
            and self.settings.textgrid_auth_token
            and self.settings.textgrid_from_number
        ):
            self.request_sender(
                build_outbound_sms_request(
                    account_sid=self.settings.textgrid_account_sid,
                    auth_token=self.settings.textgrid_auth_token,
                    from_number=self.settings.textgrid_from_number,
                    to_number=lead.phone,
                    body=message,
                    base_url=self.settings.textgrid_sms_url or "https://api.textgrid.com",
                )
            )
        if lead.email and self.settings.resend_api_key and self.settings.resend_from_email:
            self.request_sender(
                build_send_email_request(
                    api_key=self.settings.resend_api_key,
                    from_email=self.settings.resend_from_email,
                    to_email=lead.email,
                    subject="Your lease-option appointment is confirmed",
                    text_body=message,
                )
            )


class _SequenceEnrollmentAdapter:
    def __init__(
        self,
        *,
        contacts: ContactsRepository | None = None,
        sequences: SequencesRepository | None = None,
    ) -> None:
        self.contacts = contacts or ContactsRepository()
        self.sequences = sequences or SequencesRepository()

    def suppress_for_booked_lead(self, *, lead_id: str) -> None:
        lead = self.contacts.get_lead(lead_id)
        if lead is None:
            return
        enrollment = self.sequences.find_active(
            business_id=lead.business_id,
            environment=lead.environment,
            contact_id=lead.id,
            sequence_key=LEASE_OPTION_SEQUENCE_KEY,
        )
        if enrollment is None:
            return
        self.sequences.stop(
            enrollment.id,
            business_id=lead.business_id,
            environment=lead.environment,
        )

    def enroll_non_booker(self, *, lead_id: str, business_id: str, environment: str) -> None:
        lead = self.contacts.get_lead(lead_id)
        if lead is None:
            return
        self.sequences.create(
            business_id=business_id,
            environment=environment,
            contact_id=lead.id,
            sequence_key=LEASE_OPTION_SEQUENCE_KEY,
        )


class BookingService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        calcom_adapter: CalcomWebhookAdapter | None = None,
        booking_repository: BookingStateRepository | None = None,
        appointment_notifier: AppointmentNotifier | None = None,
        sequence_service: SequenceEnrollmentService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.calcom_adapter = calcom_adapter or _DefaultCalcomWebhookAdapter(self.settings)
        self.booking_repository = booking_repository or _MarketingBookingStateRepository()
        self.appointment_notifier = appointment_notifier or _ConfiguredAppointmentNotifier(settings=self.settings)
        self.sequence_service = sequence_service or _SequenceEnrollmentAdapter()

    def handle_calcom_webhook(
        self,
        payload: dict[str, Any],
        *,
        signature: str | None,
        raw_body: bytes | None = None,
    ) -> dict[str, str]:
        event = self.calcom_adapter.normalize(payload, signature=signature, raw_body=raw_body)
        newly_booked = self.booking_repository.apply_booking_event(event)
        if newly_booked:
            self.appointment_notifier.send_appointment_confirmation(lead_id=event.lead_id)
        if event.booking_status in {"booked", "rescheduled"}:
            self.sequence_service.suppress_for_booked_lead(lead_id=event.lead_id)
        return {"status": "processed", "lead_id": event.lead_id, "booking_status": event.booking_status}

    def run_non_booker_check(self, request: NonBookerCheckRequest) -> dict[str, str | bool | int]:
        booking_status = self.booking_repository.get_booking_status(request.lead_id)
        if booking_status != "pending":
            return {"booking_status": booking_status, "should_enroll_in_sequence": False}
        self.sequence_service.enroll_non_booker(
            lead_id=request.lead_id,
            business_id=request.business_id,
            environment=request.environment,
        )
        return {"booking_status": booking_status, "should_enroll_in_sequence": True, "start_day": 0}

    def get_lease_option_sequence_guard(
        self,
        request: LeaseOptionSequenceGuardRequest,
    ) -> dict[str, str | bool]:
        booking_status = self.booking_repository.get_booking_status(request.lead_id)
        sequence_status: SequenceStatus = "active" if booking_status == "pending" else "stopped"
        return {
            "booking_status": booking_status,
            "sequence_status": sequence_status,
            "opted_out": False,
        }

    def create_manual_call_task(self, request: ManualCallTaskRequest) -> dict[str, str]:
        lead = ContactsRepository().get_lead(request.lead_id)
        if lead is None:
            return {"task_id": f"manual_call_{request.lead_id}_{request.sequence_day}", "status": "open"}
        task = TasksRepository().create_manual_call(
            business_id=lead.business_id,
            environment=lead.environment,
            contact_id=lead.id,
            title=f"Call lead: {request.reason} (day {request.sequence_day})",
        )
        return {"task_id": task.id, "status": str(task.status)}


def _default_request_sender(outbound_request: dict[str, Any]) -> None:
    headers = {
        str(key): str(value)
        for key, value in dict(outbound_request.get("headers") or {}).items()
    }
    payload = outbound_request.get("payload")
    content_type = headers.get("Content-Type", "")
    if payload is None:
        body = None
    elif content_type == "application/x-www-form-urlencoded":
        from urllib.parse import urlencode

        body = urlencode(payload).encode("utf-8")
    else:
        body = json.dumps(payload).encode("utf-8")
    req = http_request.Request(
        str(outbound_request["endpoint"]),
        data=body,
        headers=headers,
        method="POST",
    )
    with http_request.urlopen(req, timeout=10):
        return None


booking_service = BookingService()
