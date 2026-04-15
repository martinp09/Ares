from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings


def _build_endpoint(settings: Settings) -> str:
    if settings.textgrid_sms_url:
        return settings.textgrid_sms_url
    if settings.textgrid_account_sid:
        return f"{settings.textgrid_base_url.rstrip('/')}/2010-04-01/Accounts/{settings.textgrid_account_sid}/Messages.json"
    raise RuntimeError("TEXTGRID_SMS_URL or TEXTGRID_ACCOUNT_SID is required")


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {"message": response.text}
    return payload if isinstance(payload, dict) else {"data": payload}


def _extract_error(payload: dict[str, Any], response: httpx.Response) -> str:
    for key in ("message", "Message", "error", "detail", "description"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict):
            for key in ("message", "detail", "description"):
                value = first.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    if response.text.strip():
        return response.text.strip()
    return f"TextGrid request failed with HTTP {response.status_code}"


def get_textgrid_status(settings: Settings) -> dict[str, Any]:
    configured = bool(settings.textgrid_account_sid and settings.textgrid_auth_token and settings.textgrid_from_number)
    endpoint = settings.textgrid_sms_url
    if endpoint is None and settings.textgrid_account_sid:
        endpoint = _build_endpoint(settings)

    detail = None
    if not configured:
        missing = [
            name
            for name, present in (
                ("TEXTGRID_ACCOUNT_SID", bool(settings.textgrid_account_sid)),
                ("TEXTGRID_AUTH_TOKEN", bool(settings.textgrid_auth_token)),
                ("TEXTGRID_FROM_NUMBER", bool(settings.textgrid_from_number)),
            )
            if not present
        ]
        detail = f"Missing: {', '.join(missing)}"

    return {
        "provider": "textgrid",
        "configured": configured,
        "can_send": configured,
        "sender_identity": settings.textgrid_from_number,
        "endpoint": endpoint,
        "details": detail,
        "checked_at": datetime.now(UTC),
    }


def send_test_sms(settings: Settings, *, to: str, body: str) -> dict[str, Any]:
    endpoint = _build_endpoint(settings)
    if not settings.textgrid_account_sid:
        raise RuntimeError("TEXTGRID_ACCOUNT_SID is required")
    if not settings.textgrid_auth_token:
        raise RuntimeError("TEXTGRID_AUTH_TOKEN is required")
    if not settings.textgrid_from_number:
        raise RuntimeError("TEXTGRID_FROM_NUMBER is required")

    response = httpx.post(
        endpoint,
        auth=(settings.textgrid_account_sid, settings.textgrid_auth_token),
        data={"To": to, "From": settings.textgrid_from_number, "Body": body},
        headers={"Accept": "application/json"},
        timeout=settings.provider_request_timeout_seconds,
    )
    payload = _safe_json(response)

    if response.is_error:
        raise RuntimeError(_extract_error(payload, response))

    provider_message_id = (
        payload.get("sid")
        or payload.get("messageSid")
        or payload.get("message_id")
        or payload.get("id")
    )
    provider_status = str(payload.get("status") or "queued").lower()
    return {
        "channel": "sms",
        "provider": "textgrid",
        "status": provider_status if provider_status in {"queued", "sent", "delivered"} else "queued",
        "provider_message_id": str(provider_message_id) if provider_message_id is not None else None,
        "to": to,
        "from_identity": settings.textgrid_from_number,
        "attempted_at": datetime.now(UTC),
        "error_message": None,
    }
