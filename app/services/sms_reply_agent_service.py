from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings, get_settings
from app.providers.textgrid import normalize_phone_number


ProviderComplete = Callable[[dict[str, Any]], str | None]

STOP_TERMS = {"stop", "unsubscribe", "cancel", "remove me", "do not text", "dont text"}
WRONG_NUMBER_TERMS = {"wrong number", "wrong person", "not me"}
LEGAL_TERMS = {"attorney", "lawyer", "court", "sue", "probate court", "lawsuit", "legal advice", "tax advice"}
ANGRY_TERMS = {"scam", "fraud", "harass", "harassment", "leave me alone", "reported"}
INTEREST_TERMS = {"yes", "interested", "call me", "tell me more", "offer", "how much", "cash"}
APPOINTMENT_TERMS = {"schedule", "appointment", "meet", "call tomorrow", "call today", "call me tomorrow"}
QUESTION_STARTERS = ("what", "how", "why", "when", "where", "who", "can", "could", "would", "do", "does", "is", "are")
URGENT_TERMS = {"asap", "urgent", "today", "now"}

AUTO_ACK_INTENTS = {"interested", "question", "appointment_request", "unknown"}
LLM_REPLY_ACTIONS = {"draft_only", "auto_ack"}
MAX_SMS_REPLY_CHARS = 280
UNSAFE_REPLY_TERMS = {
    "guarantee",
    "legal advice",
    "tax advice",
    "attorney advised",
    "court will",
    "you must",
    "we already own",
    "approved funding",
    "wire money",
    "bank account",
}


class SmsReplyContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    message_id: str | None = None
    contact_id: str | None = None
    from_number: str = Field(min_length=1)
    to_number: str = Field(min_length=1)
    body: str = Field(min_length=1)
    resolved: bool
    ambiguous: bool
    sms_consent: bool
    suppressed: bool
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    lead_context: dict[str, Any] = Field(default_factory=dict)


class SmsReplyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    intent: str = Field(min_length=1)
    source_lane: str = Field(min_length=1)
    temperature: str = Field(min_length=1)
    urgency: str = Field(min_length=1)
    action: str = Field(min_length=1)
    suggested_body: str | None = None
    confidence: float = Field(ge=0, le=1)
    policy_reason: str = Field(min_length=1)
    suppress_contact: bool = False
    handoff_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmsReplyAgentService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        provider_complete: ProviderComplete | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider_complete = provider_complete

    def decide(self, context: SmsReplyContext) -> SmsReplyDecision:
        normalized_body = _normalize_text(context.body)
        intent = _classify_intent(normalized_body)
        source_lane = _source_lane(context, normalized_body)
        urgency = _urgency(intent, normalized_body)
        suppress_contact = intent == "stop"
        action, policy_reason, handoff_required = self._policy(context=context, intent=intent, urgency=urgency)
        suggested_body = _suggested_body(intent, source_lane, context) if action in LLM_REPLY_ACTIONS else None
        llm_body, provider_used, llm_error = self._llm_suggested_body(
            context=context,
            intent=intent,
            source_lane=source_lane,
            action=action,
            fallback_body=suggested_body,
        )
        if llm_body is not None:
            suggested_body = llm_body

        return SmsReplyDecision(
            intent=intent,
            source_lane=source_lane,
            temperature=_temperature(intent=intent, action=action, urgency=urgency),
            urgency=urgency,
            action=action,
            suggested_body=suggested_body,
            confidence=_confidence(intent, context),
            policy_reason=policy_reason,
            suppress_contact=suppress_contact,
            handoff_required=handoff_required,
            metadata={
                "job_id": context.job_id,
                "message_id": context.message_id,
                "contact_id": context.contact_id,
                "provider_completion_used": provider_used,
                "llm_reply_error": llm_error,
                "recent_message_count": len(context.recent_messages),
                "lead_context_keys": sorted(context.lead_context.keys()),
                "prompt_version": self.settings.sms_agent_prompt_version,
            },
        )

    def _policy(self, *, context: SmsReplyContext, intent: str, urgency: str) -> tuple[str, str, bool]:
        if intent == "stop":
            return "human_handoff", "Stop request", True
        if intent == "wrong_number":
            return "human_handoff", "Wrong-number reply", True
        if intent == "legal_sensitive":
            return "human_handoff", "Legal-sensitive reply", True
        if context.ambiguous or not context.resolved:
            return "human_handoff", "Ambiguous or unresolved sender", True
        if context.suppressed:
            return "human_handoff", "Contact is suppressed", True
        if not context.sms_consent:
            return "human_handoff", "Missing SMS consent", True
        if urgency == "urgent":
            return "human_handoff", "Urgent reply requires human handoff", True
        if self.settings.sms_agent_mode == "record_only":
            return "record_only", "SMS agent is in record-only mode", False
        if (
            self.settings.provider_live_sends_enabled
            and self.settings.sms_agent_auto_replies_enabled
            and self.settings.sms_agent_mode == "auto_ack"
            and intent in AUTO_ACK_INTENTS
        ):
            if not _sender_allowed_for_auto_reply(self.settings.sms_agent_allowed_from_numbers, context.from_number):
                return "draft_only", "Sender is outside SMS auto-reply allowlist", False
            return "auto_ack", "Auto acknowledgement allowed by policy gates", False
        return "draft_only", "Draft-only mode or live reply gates disabled", False

    def _llm_suggested_body(
        self,
        *,
        context: SmsReplyContext,
        intent: str,
        source_lane: str,
        action: str,
        fallback_body: str | None,
    ) -> tuple[str | None, bool, str | None]:
        if action not in LLM_REPLY_ACTIONS or fallback_body is None:
            return None, False, None
        if not self.settings.sms_agent_llm_replies_enabled:
            return None, False, None
        callback = self.provider_complete or _configured_provider_complete(self.settings)
        if callback is None:
            return None, False, "llm_provider_not_configured"
        prompt = _build_llm_prompt(
            context=context,
            intent=intent,
            source_lane=source_lane,
            action=action,
            fallback_body=fallback_body,
            model=self.settings.sms_agent_llm_model,
        )
        try:
            raw_reply = callback(prompt)
        except Exception as exc:  # noqa: BLE001 - provider failure must fall back safely.
            return None, False, f"{type(exc).__name__}: {str(exc)[:160]}"
        safe_reply = _safe_llm_reply(raw_reply)
        if safe_reply is None:
            return None, False, "unsafe_or_empty_llm_reply"
        return safe_reply, True, None


def _normalize_text(body: str) -> str:
    return re.sub(r"\s+", " ", body.casefold()).strip()


def _classify_intent(body: str) -> str:
    if _has_term(body, STOP_TERMS):
        return "stop"
    if _has_term(body, WRONG_NUMBER_TERMS):
        return "wrong_number"
    if _has_term(body, LEGAL_TERMS | ANGRY_TERMS):
        return "legal_sensitive"
    if _has_term(body, APPOINTMENT_TERMS):
        return "appointment_request"
    if _has_term(body, INTEREST_TERMS):
        return "interested"
    if "?" in body or body.startswith(QUESTION_STARTERS):
        return "question"
    return "unknown"


def _has_term(body: str, terms: set[str]) -> bool:
    return any(_contains_term(body, term) for term in terms)


def _contains_term(body: str, term: str) -> bool:
    if " " in term:
        return term in body
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", body) is not None


def _source_lane(context: SmsReplyContext, body: str) -> str:
    source_lane = context.lead_context.get("source_lane")
    if isinstance(source_lane, str) and source_lane.strip():
        return source_lane.strip()
    lead_lane = context.lead_context.get("lane")
    if isinstance(lead_lane, str) and lead_lane.strip():
        return _normalize_lane(lead_lane)
    if _has_term(body, {"probate", "estate", "heir", "inherited", "executor", "administrator"}):
        return "outbound_probate"
    if _has_term(body, {"lease option", "rent to own", "seller finance", "creative finance", "booking"}):
        return "inbound_lease_option"
    return "unknown"


def _normalize_lane(value: str) -> str:
    normalized = value.casefold().replace("-", "_").replace(" ", "_")
    if "probate" in normalized:
        return "outbound_probate"
    if "lease" in normalized or "rent_to_own" in normalized:
        return "inbound_lease_option"
    return normalized or "unknown"


def _urgency(intent: str, body: str) -> str:
    if intent in {"stop", "wrong_number", "legal_sensitive"}:
        return "urgent"
    if _has_term(body, URGENT_TERMS):
        return "urgent"
    if intent == "appointment_request":
        return "normal"
    return "low"


def _temperature(*, intent: str, action: str, urgency: str) -> str:
    if action == "human_handoff" or urgency == "urgent":
        return "hot"
    if intent in {"interested", "appointment_request"}:
        return "warm"
    return "cold"


def _confidence(intent: str, context: SmsReplyContext) -> float:
    if context.ambiguous or not context.resolved:
        return 0.35
    if intent in {"stop", "wrong_number", "legal_sensitive"}:
        return 0.95
    if intent in {"interested", "appointment_request", "question"}:
        return 0.8
    return 0.55


def _sender_allowed_for_auto_reply(allowed_numbers: str | None, from_number: str) -> bool:
    if not allowed_numbers or not allowed_numbers.strip():
        return True
    allowed = {
        normalize_phone_number(part.strip())
        for part in re.split(r"[,\n]", allowed_numbers)
        if part.strip()
    }
    return normalize_phone_number(from_number) in allowed


def _suggested_body(intent: str, source_lane: str, context: SmsReplyContext) -> str:
    smoke_body = _owned_number_smoke_body(context)
    if smoke_body is not None:
        return smoke_body
    body = _normalize_text(context.body)
    if intent == "appointment_request":
        return "Thanks for reaching out. I can help coordinate a time for a quick call."
    if intent == "question":
        if _has_identity_question(body):
            return "This is Martin with Limitless Home Solution. I’m following up on a property question and trying to make sure I have the right person before assuming anything."
        return "Thanks for the question. I can review the property context and follow up with the right details."
    if intent == "interested" and source_lane == "outbound_probate":
        return "Thanks for replying. First I want to make sure I’m speaking with the right person for the property before assuming anything."
    if intent == "interested" and source_lane == "inbound_lease_option":
        return "Thanks for replying. What property address or city/state are you asking about?"
    return "Thanks for replying. What property address or city/state should I look at?"


def _has_identity_question(body: str) -> bool:
    return any(
        phrase in body
        for phrase in (
            "who is this",
            "who's this",
            "who are you",
            "what is this",
            "info on you",
            "information on you",
        )
    )


def _owned_number_smoke_body(context: SmsReplyContext) -> str | None:
    if context.lead_context.get("property_type") != "owned_number_smoke":
        return None
    body = _normalize_text(context.body)
    if _has_identity_question(body):
        return (
            "This is Ares, the Limitless SMS qualification test agent. "
            "I can answer in short texts and ask seller-style qualification questions. "
            "What property address or city/state should I look at?"
        )
    outbound_count = sum(1 for message in context.recent_messages if message.get("direction") == "outbound")
    questions = [
        "What property address or city/state should I look at?",
        "Are you the owner/decision maker, or helping someone who is?",
        "What has you considering selling or getting options right now?",
        "How soon would you want to do something if the numbers make sense?",
        "What condition is it in - vacant, rented, needs repairs, inherited, or something else?",
        "Do you have a price in mind, or would you rather have us review it and make an offer?",
        "Thanks. I have enough for the smoke test and would route this to Martin for review next.",
    ]
    return questions[min(outbound_count, len(questions) - 1)]


def _build_llm_prompt(
    *,
    context: SmsReplyContext,
    intent: str,
    source_lane: str,
    action: str,
    fallback_body: str,
    model: str,
) -> dict[str, Any]:
    recent = [
        {
            "direction": message.get("direction"),
            "body": str(message.get("body") or "")[:220],
        }
        for message in context.recent_messages[-6:]
    ]
    return {
        "model": model,
        "system": (
            "You write one SMS reply for a real-estate acquisitions operator. "
            "Sound like a real helpful human, not a deterministic chatbot. "
            "Do not change the policy action, do not make legal/tax claims, do not pressure, "
            "do not promise a guaranteed offer, and do not invent facts. "
            "Ask one natural next qualification question unless answering a direct identity question. "
            f"Keep it under {MAX_SMS_REPLY_CHARS} characters. Return only JSON with a reply field."
        ),
        "input": {
            "incoming_sms": context.body,
            "intent": intent,
            "source_lane": source_lane,
            "action": action,
            "fallback_reply": fallback_body,
            "lead_context": _redacted_context(context.lead_context),
            "recent_messages": recent,
            "goals": [
                "answer direct questions briefly",
                "move toward property address/city-state, authority, motivation, timeline, condition, and price expectation",
                "one question per text",
                "handoff to Martin when urgent, legal, angry, wrong-number, or stop appears",
            ],
        },
    }


def _redacted_context(value: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "source_lane",
        "lane",
        "property_address",
        "property_type",
        "timeline_to_sell",
        "seller_goal",
        "booking_status",
        "notes",
        "sms_consent",
    }
    return {key: value[key] for key in sorted(value) if key in allowed_keys and value[key] not in (None, "")}


def _safe_llm_reply(raw_reply: str | None) -> str | None:
    if raw_reply is None:
        return None
    text = _extract_reply_text(raw_reply)
    text = re.sub(r"\s+", " ", text).strip().strip('"').strip("'")
    if not text:
        return None
    if len(text) > MAX_SMS_REPLY_CHARS:
        return None
    normalized = _normalize_text(text)
    if any(term in normalized for term in UNSAFE_REPLY_TERMS):
        return None
    if normalized.count("?") > 2:
        return None
    return text


def _extract_reply_text(raw_reply: str) -> str:
    stripped = str(raw_reply).strip()
    if not stripped:
        return ""
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped
    if isinstance(parsed, dict):
        reply = parsed.get("reply")
        return "" if reply is None else str(reply)
    if isinstance(parsed, str):
        return parsed
    return ""


def _configured_provider_complete(settings: Settings) -> ProviderComplete | None:
    if settings.sms_agent_llm_provider == "openai_compat":
        if not settings.openai_compat_api_key:
            return None
        return lambda prompt: _call_openai_compat(settings, prompt)
    if settings.sms_agent_llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            return None
        return lambda prompt: _call_anthropic(settings, prompt)
    return None


def _call_openai_compat(settings: Settings, prompt: dict[str, Any]) -> str | None:
    base_url = (settings.openai_compat_base_url or "https://api.openai.com/v1").rstrip("/")
    payload = {
        "model": settings.sms_agent_llm_model,
        "temperature": settings.sms_agent_llm_temperature,
        "messages": [
            {"role": "system", "content": str(prompt["system"])},
            {"role": "user", "content": json.dumps(prompt["input"], ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
    }
    body = _json_post(
        f"{base_url}/chat/completions",
        payload=payload,
        headers={"Authorization": f"Bearer {settings.openai_compat_api_key}"},
        timeout=settings.sms_agent_llm_timeout_seconds,
    )
    choices = body.get("choices") if isinstance(body, dict) else None
    if not choices:
        return None
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return None if content is None else str(content)


def _call_anthropic(settings: Settings, prompt: dict[str, Any]) -> str | None:
    payload = {
        "model": settings.sms_agent_llm_model,
        "max_tokens": 120,
        "temperature": settings.sms_agent_llm_temperature,
        "system": str(prompt["system"]),
        "messages": [{"role": "user", "content": json.dumps(prompt["input"], ensure_ascii=False)}],
    }
    body = _json_post(
        f"{settings.anthropic_base_url.rstrip('/')}/v1/messages",
        payload=payload,
        headers={
            "x-api-key": str(settings.anthropic_api_key),
            "anthropic-version": "2023-06-01",
        },
        timeout=settings.sms_agent_llm_timeout_seconds,
    )
    content = body.get("content") if isinstance(body, dict) else None
    if not content:
        return None
    first = content[0]
    if not isinstance(first, dict):
        return None
    text = first.get("text")
    return None if text is None else str(text)


def _json_post(url: str, *, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AresSmsReplyAgent/1.0",
            **headers,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL is configured by operator env.
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"LLM provider HTTP {exc.code}: {error_body}") from exc
