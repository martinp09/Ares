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
    last_name: str | None = None
    property_type: str | None = None
    timeline_to_sell: str | None = None
    monthly_payment_goal: str | None = None
    asking_price_goal: str | None = None
    seller_goal: str | None = None
    notes: str | None = None
    sms_consent: bool = False
    consent_page_url: str | None = None
    consent_ip: str | None = None
    consent_user_agent: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    lp_var: str | None = None


class LeadRepository(Protocol):
    def upsert_lead(self, payload: LeadIntakePayload) -> str | None: ...


class SmsGateway(Protocol):
    def send_confirmation(self, payload: LeadIntakePayload, *, booking_url: str) -> str | None: ...


class EmailGateway(Protocol):
    def send_confirmation(self, payload: LeadIntakePayload, *, booking_url: str) -> str | None: ...


class OperatorNotifier(Protocol):
    def notify_new_lead(self, payload: LeadIntakePayload, *, lead_id: str, booking_url: str) -> str | None: ...


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
                last_name=payload.last_name,
                property_type=payload.property_type,
                timeline_to_sell=payload.timeline_to_sell,
                monthly_payment_goal=payload.monthly_payment_goal,
                asking_price_goal=payload.asking_price_goal,
                seller_goal=payload.seller_goal,
                notes=payload.notes,
                sms_consent=payload.sms_consent,
                consent_page_url=payload.consent_page_url,
                consent_ip=payload.consent_ip,
                consent_user_agent=payload.consent_user_agent,
                utm_source=payload.utm_source,
                utm_medium=payload.utm_medium,
                utm_campaign=payload.utm_campaign,
                utm_term=payload.utm_term,
                utm_content=payload.utm_content,
                lp_var=payload.lp_var,
            )
        )
        return record.id


class _NoopSmsGateway:
    def send_confirmation(self, payload: LeadIntakePayload, *, booking_url: str) -> str | None:
        return None


class _NoopEmailGateway:
    def send_confirmation(self, payload: LeadIntakePayload, *, booking_url: str) -> str | None:
        return None


class _NoopOperatorNotifier:
    def notify_new_lead(self, payload: LeadIntakePayload, *, lead_id: str, booking_url: str) -> str | None:
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

    def send_confirmation(self, payload: LeadIntakePayload, *, booking_url: str) -> str | None:
        outbound_request = build_outbound_sms_request(
            account_sid=self.account_sid,
            auth_token=self.auth_token,
            from_number=self.from_number,
            to_number=payload.phone,
            body=_build_confirmation_message(payload, booking_url=booking_url),
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

    def send_confirmation(self, payload: LeadIntakePayload, *, booking_url: str) -> str | None:
        if not payload.email:
            return None
        return _extract_provider_message_id(
            self.email_sender(
                self.settings,
                to=payload.email,
                subject="Your lease-option review call",
                text=_build_confirmation_message(payload, booking_url=booking_url),
            )
        )


class _ConfiguredSlackOperatorNotifier:
    def __init__(
        self,
        *,
        token: str,
        channel: str,
        request_sender: RequestSender,
    ) -> None:
        self.token = token
        self.channel = channel
        self.request_sender = request_sender

    def notify_new_lead(self, payload: LeadIntakePayload, *, lead_id: str, booking_url: str) -> str | None:
        last_name = f" {payload.last_name}" if payload.last_name else ""
        lead_name = f"{payload.first_name}{last_name}"
        text = f"New lease-option lead: {lead_name} — {payload.property_address}"
        fields = [
            {"type": "mrkdwn", "text": f"*Lead:*\n{lead_name}"},
            {"type": "mrkdwn", "text": f"*Phone:*\n{payload.phone}"},
            {"type": "mrkdwn", "text": f"*Email:*\n{payload.email or 'not provided'}"},
            {"type": "mrkdwn", "text": f"*Timeline:*\n{payload.timeline_to_sell or 'not provided'}"},
            {"type": "mrkdwn", "text": f"*Asking goal:*\n{payload.asking_price_goal or 'not provided'}"},
            {"type": "mrkdwn", "text": f"*LP variant:*\n{payload.lp_var or 'not provided'}"},
        ]
        provider_response = self.request_sender(
            {
                "endpoint": "https://slack.com/api/chat.postMessage",
                "headers": {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                "payload": {
                    "channel": self.channel,
                    "text": text,
                    "unfurl_links": False,
                    "unfurl_media": False,
                    "blocks": [
                        {"type": "header", "text": {"type": "plain_text", "text": "New lease-option lead"}},
                        {"type": "section", "fields": fields},
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Property:*\n{payload.property_address}"}},
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Booking link:* {booking_url}"}},
                        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"lead_id={lead_id} • source={payload.utm_source or 'unknown'}"}]},
                    ],
                },
            }
        )
        if isinstance(provider_response, dict) and provider_response.get("ok") is False:
            raise RuntimeError(str(provider_response.get("error") or "Slack notification failed"))
        if isinstance(provider_response, dict):
            channel = provider_response.get("channel")
            ts = provider_response.get("ts")
            if channel and ts:
                return f"{channel}:{ts}"
        return _extract_provider_message_id(provider_response)


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
        with request.urlopen(req, timeout=5):  # nosec B310
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
    if not settings.provider_live_sends_enabled or not settings.trigger_secret_key:
        return _NoopTriggerScheduler()
    return _TriggerHttpScheduler(
        secret_key=settings.trigger_secret_key,
        api_url=settings.trigger_api_url or _DEFAULT_TRIGGER_API_URL,
        task_id=settings.trigger_non_booker_check_task_id or _DEFAULT_NON_BOOKER_CHECK_TASK_ID,
        delay=_DEFAULT_NON_BOOKER_CHECK_DELAY,
    )


def _build_confirmation_message(payload: LeadIntakePayload, *, booking_url: str | None = None) -> str:
    if booking_url:
        return (
            f"Thanks {payload.first_name}, we got your lease-option request. "
            f"Book your review call here: {booking_url}. Reply STOP to opt out."
        )
    return f"Thanks {payload.first_name}, we got your lease-option request and will follow up shortly. Reply STOP to opt out."


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
    with request.urlopen(req, timeout=10) as response:  # nosec B310
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
        operator_notifier: OperatorNotifier | None = None,
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
        self.operator_notifier = operator_notifier or self._build_operator_notifier(
            active_settings,
            request_sender=active_request_sender,
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
        booking_url = self.booking_link_provider.get_booking_url(payload, lead_id=lead_id)
        side_effects: list[SideEffectStatus] = []
        side_effects.append(
            self._run_side_effect(
                payload=payload,
                lead_id=lead_id,
                name="confirmation_sms",
                skipped=not payload.sms_consent or isinstance(self.sms_gateway, _NoopSmsGateway),
                channel="sms",
                provider="textgrid",
                body=_build_confirmation_message(payload, booking_url=booking_url),
                send=lambda: self.sms_gateway.send_confirmation(payload, booking_url=booking_url),
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
                body=_build_confirmation_message(payload, booking_url=booking_url),
                send=lambda: self.email_gateway.send_confirmation(payload, booking_url=booking_url),
            )
        )
        side_effects.append(
            self._run_side_effect(
                payload=payload,
                lead_id=lead_id,
                name="operator_slack_notification",
                skipped=isinstance(self.operator_notifier, _NoopOperatorNotifier),
                provider="slack",
                send=lambda: self.operator_notifier.notify_new_lead(
                    payload,
                    lead_id=lead_id,
                    booking_url=booking_url,
                ),
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
            "booking_url": booking_url,
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
        if not settings.provider_live_sends_enabled:
            return _NoopSmsGateway()
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
        if not settings.provider_live_sends_enabled:
            return _NoopEmailGateway()
        if settings.resend_api_key and settings.resend_from_email:
            return _ConfiguredResendEmailGateway(
                settings=settings,
                email_sender=email_sender,
            )
        return _NoopEmailGateway()

    @staticmethod
    def _build_operator_notifier(settings: Settings, *, request_sender: RequestSender) -> OperatorNotifier:
        channel = settings.slack_channel_intake or settings.slack_channel_leads
        if settings.slack_bot_token and channel:
            return _ConfiguredSlackOperatorNotifier(
                token=settings.slack_bot_token,
                channel=channel,
                request_sender=request_sender,
            )
        return _NoopOperatorNotifier()

    @staticmethod
    def _build_booking_link_provider(settings: Settings) -> BookingLinkProvider:
        if settings.cal_booking_url:
            return _ConfiguredCalBookingLinkProvider(booking_url=settings.cal_booking_url)
        return _DefaultBookingLinkProvider()


marketing_lead_service = MarketingLeadService()
