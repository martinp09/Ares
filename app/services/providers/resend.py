from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings


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
    return f"Resend request failed with HTTP {response.status_code}"


def get_resend_status(settings: Settings) -> dict[str, Any]:
    configured = bool(settings.resend_api_key and settings.resend_from_email)
    detail = None
    if not configured:
        missing = [
            name
            for name, present in (
                ("RESEND_API_KEY", bool(settings.resend_api_key)),
                ("RESEND_FROM_EMAIL", bool(settings.resend_from_email)),
            )
            if not present
        ]
        detail = f"Missing: {', '.join(missing)}"

    return {
        "provider": "resend",
        "configured": configured,
        "can_send": configured,
        "sender_identity": settings.resend_from_email,
        "endpoint": settings.resend_email_url,
        "details": detail,
        "checked_at": datetime.now(UTC),
    }


def send_test_email(
    settings: Settings,
    *,
    to: str,
    subject: str,
    text: str,
    html: str | None = None,
) -> dict[str, Any]:
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is required")
    if not settings.resend_from_email:
        raise RuntimeError("RESEND_FROM_EMAIL is required")

    payload: dict[str, Any] = {
        "from": settings.resend_from_email,
        "to": to,
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html
    if settings.resend_reply_to_email:
        payload["reply_to"] = settings.resend_reply_to_email

    response = httpx.post(
        settings.resend_email_url,
        headers={"Authorization": f"Bearer {settings.resend_api_key}", "Accept": "application/json"},
        json=payload,
        timeout=settings.provider_request_timeout_seconds,
    )
    payload_data = _safe_json(response)

    if response.is_error:
        raise RuntimeError(_extract_error(payload_data, response))

    response_id = payload_data.get("id") or payload_data.get("data", {}).get("id")
    return {
        "channel": "email",
        "provider": "resend",
        "status": "queued",
        "provider_message_id": str(response_id) if response_id is not None else None,
        "to": to,
        "from_identity": settings.resend_from_email,
        "attempted_at": datetime.now(UTC),
        "error_message": None,
    }
