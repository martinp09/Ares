from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any, Callable, Protocol
from urllib import request
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.db.conversations import ConversationsRepository
from app.db.contacts import ContactsRepository
from app.db.messages import MessagesRepository
from app.db.tasks import TasksRepository
from app.models.marketing_leads import LeadUpsertRequest
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType
from app.services.providers.resend import send_test_email as send_resend_email
from app.providers.textgrid import build_outbound_sms_request

_DEFAULT_TRIGGER_API_URL = "https://api.trigger.dev"
_DEFAULT_NON_BOOKER_CHECK_TASK_ID = "marketing-check-submitted-lead-booking"
_DEFAULT_NON_BOOKER_CHECK_DELAY = "5m"


@dataclass(slots=True)
class LeadIntakePayload:
    business_id: str
    environment: str
    first_name: str
    phone: str
    email: str | None
    property_address: str
    booking_status: str = "pending"


class LeadRepository(Protocol):
    def upsert_lead(self, payload: LeadIntakePayload) -> str | None: ...


class SmsGateway(Protocol):
    def send_confirmation(self, payload: LeadIntakePayload) -> str | None: ...


class EmailGateway(Protocol):
    def send_confirmation(self, payload: LeadIntakePayload) -> str | None: ...


class BookingLinkProvider(Protocol):
    def get_booking_url(self, payload: LeadIntakePayload, *, lead_id: str) -> str: ...


class TriggerScheduler(Protocol):
    def schedule_non_booker_check(self, payload: LeadIntakePayload, *, lead_id: str) -> None: ...


RequestSender = Callable[[dict[str, Any]], Any]
ResendEmailSender = Callable[..., dict[str, Any]]


class SideEffectStatus(dict[str, str | None]):
    pass


def _extract_provider_message_id(response: Any) -> str | None:
    if isinstance(response, dict):
        for key in ("sid", "message_sid", "MessageSid", "id", "provider_message_id"):
            value = response.get(key)
            if value:
                return str(value)
    return None


class _NoopLeadRepository:
    def upsert_lead(self, payload: LeadIntakePayload) -> str | None:
        return None


class _ContactsLeadRepository:
    def __init__(self, contacts: ContactsRepository | None = None) -> None:
        self.contacts = contacts or ContactsRepository()

    def upsert_lead(self, payload: LeadIntakePayload) -> str | None:
        record = self.contacts.upsert_lead(
            LeadUpsertRequest(
                business_id=payload.business_id,
                environment=payload.environment,
                first_name=payload.first_name,
                phone=payload.phone,
                email=payload.email,
                property_address=payload.property_address,
                booking_status=payload.booking_status,
            )
        )
        return record.id


class _NoopSmsGateway:
    def send_confirmation(self, payload: LeadIntakePayload) -> str | None:
        return None


class _NoopEmailGateway:
    def send_confirmation(self, payload: LeadIntakePayload) -> str | None:
        return None


class _ConfiguredTextgridSmsGateway:
    def __init__(
        self,
        *,
        account_sid: str,
        auth_token: str,
        from_number: str,
        request_sender: RequestSender,
        sms_url: str | None = None,
        status_callback_url: str | None = None,
    ) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.request_sender = request_sender
        self.sms_url = sms_url
        self.status_callback_url = status_callback_url

    def send_confirmation(self, payload: LeadIntakePayload) -> str | None:
        outbound_request = build_outbound_sms_request(
            account_sid=self.account_sid,
            auth_token=self.auth_token,
            from_number=self.from_number,
            to_number=payload.phone,
            body=_build_confirmation_message(payload),
            status_callback_url=self.status_callback_url,
        )
        if self.sms_url:
            outbound_request["endpoint"] = self.sms_url
        return _extract_provider_message_id(self.request_sender(outbound_request))


class _ConfiguredResendEmailGateway:
    def __init__(
        self,
        *,
        settings: Settings,
        email_sender: ResendEmailSender,
    ) -> None:
        self.settings = settings
        self.email_sender = email_sender

    def send_confirmation(self, payload: LeadIntakePayload) -> str | None:
        if not payload.email:
            return None
        return _extract_provider_message_id(
            self.email_sender(
                self.settings,
                to=payload.email,
                subject="Thanks for your lease-option inquiry",
                text=_build_confirmation_message(payload),
            )
        )


class _DefaultBookingLinkProvider:
    def get_booking_url(self, payload: LeadIntakePayload, *, lead_id: str) -> str:
        return f"https://cal.com/booking/{lead_id}"


class _ConfiguredCalBookingLinkProvider:
    def __init__(self, *, booking_url: str | None = None) -> None:
        self.booking_url = booking_url or "https://cal.com/booking"

    def get_booking_url(self, payload: LeadIntakePayload, *, lead_id: str) -> str:
        parsed = urlparse(self.booking_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(
            {
                "lead_id": lead_id,
                "first_name": payload.first_name,
                "phone": payload.phone,
                "property_address": payload.property_address,
            }
        )
        if payload.email:
            query["email"] = payload.email
        return urlunparse(parsed._replace(query=urlencode(query)))


class _NoopTriggerScheduler:
    def schedule_non_booker_check(self, payload: LeadIntakePayload, *, lead_id: str) -> None:
        return None


class _TriggerHttpScheduler:
    def __init__(
        self,
        *,
        secret_key: str,
        api_url: str = _DEFAULT_TRIGGER_API_URL,
        task_id: str = _DEFAULT_NON_BOOKER_CHECK_TASK_ID,
        delay: str = _DEFAULT_NON_BOOKER_CHECK_DELAY,
    ) -> None:
        self.secret_key = secret_key
        self.api_url = api_url.rstrip("/")
        self.task_id = task_id
        self.delay = delay

    def schedule_non_booker_check(self, payload: LeadIntakePayload, *, lead_id: str) -> None:
        body = json.dumps(
            {
                "payload": {
                    "leadId": lead_id,
                    "businessId": payload.business_id,
                    "environment": payload.environment,
                },
                "options": {"delay": self.delay},
            }
        ).encode("utf-8")
        req = request.Request(
            f"{self.api_url}/api/v1/tasks/{quote(self.task_id, safe='')}/trigger",
            data=body,
            headers={
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=5):
            return None


class _LeadIntakeSideEffectRecorder:
    def __init__(
        self,
        *,
        tasks: TasksRepository | None = None,
        contacts: ContactsRepository | None = None,
        conversations: ConversationsRepository | None = None,
        messages: MessagesRepository | None = None,
    ) -> None:
        self.tasks = tasks or TasksRepository()
        self.contacts = contacts or ContactsRepository()
        self.conversations = conversations or ConversationsRepository(self.contacts.client)
        self.messages = messages or MessagesRepository(self.contacts.client)

    def record_outbound(
        self,
        *,
        payload: LeadIntakePayload,
        lead_id: str,
        side_effect: str,
        channel: str,
        provider: str,
        body: str,
        external_message_id: str | None,
    ) -> None:
        conversation = self.conversations.get_or_create(
            business_id=payload.business_id,
            environment=payload.environment,
            contact_id=lead_id,
            channel=channel,
        )
        self.messages.append_outbound(
            business_id=payload.business_id,
            environment=payload.environment,
            contact_id=lead_id,
            conversation_id=conversation.provider_thread_id,
            channel=channel,
            provider=provider,
            body=body,
            external_message_id=external_message_id,
            metadata={"side_effect": side_effect},
        )

    def record_failure(
        self,
        *,
        payload: LeadIntakePayload,
        lead_id: str,
        side_effect: str,
        error_message: str,
    ) -> None:
        dedupe_key = f"lead_intake_side_effect:{lead_id}:{side_effect}"
        self.tasks.create(
            TaskRecord(
                business_id=payload.business_id,
                environment=payload.environment,
                title=f"Review failed lead intake side effect: {side_effect}",
                status=TaskStatus.OPEN,
                task_type=TaskType.MANUAL_REVIEW,
                priority=TaskPriority.HIGH,
                lead_id=lead_id,
                idempotency_key=dedupe_key,
                details={
                    "side_effect": side_effect,
                    "visible_in_mission_control": True,
                    "status": "failed",
                    "error_message": error_message,
                    "phone": payload.phone,
                    "email": payload.email,
                },
            ),
            dedupe_key=dedupe_key,
        )


def _build_default_trigger_scheduler(settings: Settings) -> TriggerScheduler:
    if not settings.trigger_secret_key:
        return _NoopTriggerScheduler()
    return _TriggerHttpScheduler(
        secret_key=settings.trigger_secret_key,
        api_url=settings.trigger_api_url or _DEFAULT_TRIGGER_API_URL,
        task_id=settings.trigger_non_booker_check_task_id or _DEFAULT_NON_BOOKER_CHECK_TASK_ID,
        delay=_DEFAULT_NON_BOOKER_CHECK_DELAY,
    )


def _build_confirmation_message(payload: LeadIntakePayload) -> str:
    return f"Thanks {payload.first_name}, we got your lease-option request and will follow up shortly."


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
        body = urlencode(payload).encode("utf-8")
    else:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(
        str(outbound_request["endpoint"]),
        data=body,
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        response_body = response.read()
    if not response_body:
        return None
    try:
        return json.loads(response_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return response_body.decode("utf-8", errors="replace")


class MarketingLeadService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        lead_repository: LeadRepository | None = None,
        sms_gateway: SmsGateway | None = None,
        email_gateway: EmailGateway | None = None,
        booking_link_provider: BookingLinkProvider | None = None,
        trigger_scheduler: TriggerScheduler | None = None,
        request_sender: RequestSender | None = None,
        resend_email_sender: ResendEmailSender | None = None,
        tasks: TasksRepository | None = None,
        contacts: ContactsRepository | None = None,
        conversations: ConversationsRepository | None = None,
        messages: MessagesRepository | None = None,
    ) -> None:
        active_settings = settings or get_settings()
        active_request_sender = request_sender or _default_request_sender
        self.settings = active_settings
        self.contacts = contacts or ContactsRepository()
        self.lead_repository = lead_repository or _ContactsLeadRepository(self.contacts)
        self.sms_gateway = sms_gateway or self._build_sms_gateway(
            active_settings,
            request_sender=active_request_sender,
        )
        self.email_gateway = email_gateway or self._build_email_gateway(
            active_settings,
            email_sender=resend_email_sender or send_resend_email,
        )
        self.booking_link_provider = booking_link_provider or self._build_booking_link_provider(active_settings)
        self.trigger_scheduler = trigger_scheduler or _build_default_trigger_scheduler(active_settings)
        self.side_effect_recorder = _LeadIntakeSideEffectRecorder(
            tasks=tasks,
            contacts=self.contacts,
            conversations=conversations,
            messages=messages,
        )

    def intake_lead(self, payload: LeadIntakePayload) -> dict[str, Any]:
        lead_id = self.lead_repository.upsert_lead(payload) or self._generate_lead_id()
        side_effects: list[SideEffectStatus] = []
        side_effects.append(
            self._run_side_effect(
                payload=payload,
                lead_id=lead_id,
                name="confirmation_sms",
                skipped=isinstance(self.sms_gateway, _NoopSmsGateway),
                channel="sms",
                provider="textgrid",
                body=_build_confirmation_message(payload),
                send=lambda: self.sms_gateway.send_confirmation(payload),
            )
        )
        side_effects.append(
            self._run_side_effect(
                payload=payload,
                lead_id=lead_id,
                name="confirmation_email",
                skipped=not payload.email or isinstance(self.email_gateway, _NoopEmailGateway),
                channel="email",
                provider="resend",
                body=_build_confirmation_message(payload),
                send=lambda: self.email_gateway.send_confirmation(payload),
            )
        )
        side_effects.append(
            self._run_side_effect(
                payload=payload,
                lead_id=lead_id,
                name="trigger_non_booker_check",
                skipped=isinstance(self.trigger_scheduler, _NoopTriggerScheduler),
                send=lambda: self.trigger_scheduler.schedule_non_booker_check(payload, lead_id=lead_id),
            )
        )
        return {
            "lead_id": lead_id,
            "booking_status": payload.booking_status,
            "booking_url": self.booking_link_provider.get_booking_url(payload, lead_id=lead_id),
            "side_effects": side_effects,
        }

    def _run_side_effect(
        self,
        *,
        payload: LeadIntakePayload,
        lead_id: str,
        name: str,
        skipped: bool,
        send: Callable[[], str | None],
        channel: str | None = None,
        provider: str | None = None,
        body: str | None = None,
    ) -> SideEffectStatus:
        if skipped:
            return SideEffectStatus(name=name, status="skipped", error_message=None)
        try:
            external_message_id = send()
        except Exception as exc:
            error_message = str(exc)
            self.side_effect_recorder.record_failure(
                payload=payload,
                lead_id=lead_id,
                side_effect=name,
                error_message=error_message,
            )
            return SideEffectStatus(name=name, status="failed", error_message=error_message)
        if channel is not None and provider is not None and body is not None:
            self.side_effect_recorder.record_outbound(
                payload=payload,
                lead_id=lead_id,
                side_effect=name,
                channel=channel,
                provider=provider,
                body=body,
                external_message_id=external_message_id,
            )
        return SideEffectStatus(name=name, status="queued", error_message=None)

    @staticmethod
    def _generate_lead_id() -> str:
        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"lead_{stamp}_{uuid4().hex[:6]}"

    @staticmethod
    def _build_sms_gateway(settings: Settings, *, request_sender: RequestSender) -> SmsGateway:
        if settings.textgrid_account_sid and settings.textgrid_auth_token and settings.textgrid_from_number:
            return _ConfiguredTextgridSmsGateway(
                account_sid=settings.textgrid_account_sid,
                auth_token=settings.textgrid_auth_token,
                from_number=settings.textgrid_from_number,
                request_sender=request_sender,
                sms_url=settings.textgrid_sms_url,
                status_callback_url=settings.textgrid_status_callback_url,
            )
        return _NoopSmsGateway()

    @staticmethod
    def _build_email_gateway(settings: Settings, *, email_sender: ResendEmailSender) -> EmailGateway:
        if settings.resend_api_key and settings.resend_from_email:
            return _ConfiguredResendEmailGateway(
                settings=settings,
                email_sender=email_sender,
            )
        return _NoopEmailGateway()

    @staticmethod
    def _build_booking_link_provider(settings: Settings) -> BookingLinkProvider:
        if settings.cal_booking_url:
            return _ConfiguredCalBookingLinkProvider(booking_url=settings.cal_booking_url)
        return _DefaultBookingLinkProvider()


marketing_lead_service = MarketingLeadService()
