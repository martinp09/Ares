from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol
from urllib import request as http_request

from app.core.config import Settings, get_settings
from app.db.bookings import BookingsRepository
from app.db.contacts import ContactsRepository
from app.db.conversations import ConversationsRepository
from app.db.messages import MessagesRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.sequences import SequencesRepository
from app.db.tasks import TasksRepository
from app.models.lead_events import ProviderWebhookReceiptRecord
from app.models.marketing_leads import MarketingLeadRecord
from app.models.opportunities import OpportunitySourceLane
from app.providers.calcom import normalize_booking_webhook, verify_webhook_signature
from app.providers.resend import build_send_email_request
from app.providers.textgrid import build_outbound_sms_request
from app.services.opportunity_service import OpportunityService


BookingStatus = Literal["pending", "booked", "rescheduled", "cancelled"]
SequenceStatus = Literal["active", "paused", "completed", "stopped"]
LEASE_OPTION_SEQUENCE_KEY = "lease_option_non_booker_v1"


def _extract_provider_message_id(response: Any) -> str | None:
    if isinstance(response, dict):
        for key in ("sid", "message_sid", "MessageSid", "id"):
            value = response.get(key)
            if value:
                return str(value)
    return None


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
    def send_appointment_confirmation(self, *, lead_id: str) -> dict[str, str | None]: ...


class SequenceEnrollmentService(Protocol):
    def suppress_for_booked_lead(self, *, lead_id: str) -> None: ...

    def enroll_non_booker(self, *, lead_id: str, business_id: str, environment: str) -> None: ...


class BookingMessageLogService(Protocol):
    def log_appointment_confirmation(
        self,
        *,
        lead: MarketingLeadRecord,
        provider_message_ids: dict[str, str | None] | None = None,
    ) -> None: ...


class WebhookReceiptService(Protocol):
    def record_calcom_event(
        self,
        *,
        event: NormalizedBookingEvent,
        lead: MarketingLeadRecord | None,
        payload: dict[str, Any],
    ) -> tuple[str | None, bool]: ...

    def mark_processed(self, receipt_id: str | None) -> None: ...


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
    def send_appointment_confirmation(self, *, lead_id: str) -> dict[str, str | None]:
        return {}


class _NoopWebhookReceiptService:
    def record_calcom_event(
        self,
        *,
        event: NormalizedBookingEvent,
        lead: MarketingLeadRecord | None,
        payload: dict[str, Any],
    ) -> tuple[str | None, bool]:
        return None, False

    def mark_processed(self, receipt_id: str | None) -> None:
        return None


class _NoopBookingMessageLogService:
    def log_appointment_confirmation(
        self,
        *,
        lead: MarketingLeadRecord,
        provider_message_ids: dict[str, str | None] | None = None,
    ) -> None:
        return None


class _RepositoryBookingMessageLogService:
    def __init__(
        self,
        *,
        settings: Settings,
        contacts: ContactsRepository,
        conversations: ConversationsRepository | None = None,
        messages: MessagesRepository | None = None,
    ) -> None:
        self.settings = settings
        self.contacts = contacts
        self.conversations = conversations or ConversationsRepository(self.contacts.client)
        self.messages = messages or MessagesRepository(self.contacts.client)

    def log_appointment_confirmation(
        self,
        *,
        lead: MarketingLeadRecord,
        provider_message_ids: dict[str, str | None] | None = None,
    ) -> None:
        resolved_provider_message_ids = provider_message_ids or {}
        confirmation = f"Thanks {lead.first_name}, your lease-option appointment is confirmed."
        if (
            self.settings.textgrid_account_sid
            and self.settings.textgrid_auth_token
            and self.settings.textgrid_from_number
        ):
            conversation = self.conversations.get_or_create(
                business_id=lead.business_id,
                environment=lead.environment,
                contact_id=lead.id,
                channel="sms",
            )
            self.messages.append_outbound(
                business_id=lead.business_id,
                environment=lead.environment,
                contact_id=lead.id,
                conversation_id=conversation.provider_thread_id,
                channel="sms",
                provider="textgrid",
                body=confirmation,
                external_message_id=resolved_provider_message_ids.get("sms"),
            )
        if lead.email and self.settings.resend_api_key and self.settings.resend_from_email:
            conversation = self.conversations.get_or_create(
                business_id=lead.business_id,
                environment=lead.environment,
                contact_id=lead.id,
                channel="email",
            )
            self.messages.append_outbound(
                business_id=lead.business_id,
                environment=lead.environment,
                contact_id=lead.id,
                conversation_id=conversation.provider_thread_id,
                channel="email",
                provider="resend",
                body=confirmation,
                external_message_id=resolved_provider_message_ids.get("email"),
            )


class _ProviderWebhookReceiptAdapter:
    def __init__(self, provider_webhooks: ProviderWebhooksRepository | None = None) -> None:
        self.provider_webhooks = provider_webhooks or ProviderWebhooksRepository()

    def record_calcom_event(
        self,
        *,
        event: NormalizedBookingEvent,
        lead: MarketingLeadRecord | None,
        payload: dict[str, Any],
    ) -> tuple[str | None, bool]:
        if lead is None:
            return None, False
        idempotency_seed = event.external_booking_id or f"{event.event_name}:{event.booking_status}:{event.lead_id}"
        receipt = self.provider_webhooks.record(
            ProviderWebhookReceiptRecord(
                business_id=lead.business_id,
                environment=lead.environment,
                provider="cal.com",
                event_type=event.event_name,
                idempotency_key=f"calcom:{idempotency_seed}",
                provider_event_id=event.external_booking_id,
                provider_receipt_id=event.external_booking_id,
                payload={"body": payload, "lead_id": event.lead_id, "booking_status": event.booking_status},
            )
        )
        return receipt.id, bool(receipt.deduped)

    def mark_processed(self, receipt_id: str | None) -> None:
        if receipt_id is None:
            return None
        self.provider_webhooks.mark_processed(receipt_id)


class _ConfiguredAppointmentNotifier:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        contacts: ContactsRepository | None = None,
        request_sender: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.contacts = contacts or ContactsRepository()
        self.request_sender = request_sender or _default_request_sender

    def send_appointment_confirmation(self, *, lead_id: str) -> dict[str, str | None]:
        lead = self.contacts.get_lead(lead_id)
        if lead is None:
            return {}
        provider_message_ids: dict[str, str | None] = {}
        message = f"Thanks {lead.first_name}, your lease-option appointment is confirmed."
        if (
            self.settings.textgrid_account_sid
            and self.settings.textgrid_auth_token
            and self.settings.textgrid_from_number
        ):
            provider_message_ids["sms"] = self._send_and_extract(
                build_outbound_sms_request(
                    account_sid=self.settings.textgrid_account_sid,
                    auth_token=self.settings.textgrid_auth_token,
                    from_number=self.settings.textgrid_from_number,
                    to_number=lead.phone,
                    body=message,
                    base_url=self.settings.textgrid_sms_url or "https://api.textgrid.com",
                    status_callback_url=self.settings.textgrid_status_callback_url,
                )
            )
        if lead.email and self.settings.resend_api_key and self.settings.resend_from_email:
            provider_message_ids["email"] = self._send_and_extract(
                build_send_email_request(
                    api_key=self.settings.resend_api_key,
                    from_email=self.settings.resend_from_email,
                    to_email=lead.email,
                    subject="Your lease-option appointment is confirmed",
                    text_body=message,
                )
            )
        return provider_message_ids

    def _send_and_extract(self, outbound_request: dict[str, Any]) -> str | None:
        try:
            return _extract_provider_message_id(self.request_sender(outbound_request))
        except Exception:
            return None


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
        contacts: ContactsRepository | None = None,
        webhook_receipts: WebhookReceiptService | None = None,
        opportunity_service: OpportunityService | None = None,
        sequences: SequencesRepository | None = None,
        message_log_service: BookingMessageLogService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.calcom_adapter = calcom_adapter or _DefaultCalcomWebhookAdapter(self.settings)
        self.booking_repository = booking_repository or _MarketingBookingStateRepository()
        self.appointment_notifier = appointment_notifier or _ConfiguredAppointmentNotifier(settings=self.settings)
        self.sequence_service = sequence_service or _SequenceEnrollmentAdapter()
        self.contacts = contacts or ContactsRepository()
        self.webhook_receipts = webhook_receipts or _ProviderWebhookReceiptAdapter(
            ProviderWebhooksRepository(self.contacts.client)
        )
        self.opportunity_service = opportunity_service or OpportunityService()
        self.sequences = sequences or SequencesRepository(self.contacts.client)
        self.message_log_service = message_log_service or _RepositoryBookingMessageLogService(
            settings=self.settings,
            contacts=self.contacts,
        )

    def handle_calcom_webhook(
        self,
        payload: dict[str, Any],
        *,
        signature: str | None,
        raw_body: bytes | None = None,
    ) -> dict[str, str]:
        event = self.calcom_adapter.normalize(payload, signature=signature, raw_body=raw_body)
        lead = self.contacts.get_lead(event.lead_id)
        receipt_id, deduped = self.webhook_receipts.record_calcom_event(event=event, lead=lead, payload=payload)
        if deduped:
            self.webhook_receipts.mark_processed(receipt_id)
            return {"status": "processed", "lead_id": event.lead_id, "booking_status": event.booking_status}
        newly_booked = self.booking_repository.apply_booking_event(event)
        provider_message_ids: dict[str, str | None] = {}
        if newly_booked:
            try:
                provider_message_ids = self.appointment_notifier.send_appointment_confirmation(lead_id=event.lead_id) or {}
            except Exception:
                pass
            if lead is not None:
                self.message_log_service.log_appointment_confirmation(
                    lead=lead,
                    provider_message_ids=provider_message_ids,
                )
            self._sync_opportunity(lead, event)
        if event.booking_status in {"booked", "rescheduled"}:
            self.sequence_service.suppress_for_booked_lead(lead_id=event.lead_id)
        self.webhook_receipts.mark_processed(receipt_id)
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
        if booking_status != "pending":
            return {
                "booking_status": booking_status,
                "sequence_status": "stopped",
                "opted_out": False,
            }
        sequence_status: SequenceStatus = "active"
        opted_out = False
        enrollment = self.sequences.find_latest(
            business_id=request.business_id,
            environment=request.environment,
            contact_id=request.lead_id,
            sequence_key=LEASE_OPTION_SEQUENCE_KEY,
        )
        if enrollment is not None:
            sequence_status = enrollment.status.value  # type: ignore[assignment]
            opted_out = enrollment.status.value == "stopped"
        return {
            "booking_status": booking_status,
            "sequence_status": sequence_status,
            "opted_out": opted_out,
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

    def _sync_opportunity(self, lead: MarketingLeadRecord | None, event: NormalizedBookingEvent) -> None:
        if lead is None or event.booking_status != "booked":
            return
        self.opportunity_service.create_for_contact(
            business_id=lead.business_id,
            environment=lead.environment,
            contact_id=lead.id,
            source_lane=OpportunitySourceLane.LEASE_OPTION_INBOUND,
            metadata={
                "booking_status": event.booking_status,
                "event_name": event.event_name,
            },
        )


def _default_request_sender(outbound_request: dict[str, Any]) -> Any:
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
    with http_request.urlopen(req, timeout=10) as response:
        response_body = response.read()
    if not response_body:
        return None
    try:
        return json.loads(response_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return response_body.decode("utf-8", errors="replace")


booking_service = BookingService()
