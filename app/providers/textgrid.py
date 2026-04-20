import base64
import hashlib
import hmac
from typing import Any, Mapping


def normalize_status(raw_status: str | None) -> str:
    status = str(raw_status or "").lower()
    if status in {"queued", "accepted", "sending"}:
        return "queued"
    if status == "sent":
        return "sent"
    if status == "delivered":
        return "delivered"
    if status in {"failed", "undelivered"}:
        return "failed"
    if status == "received":
        return "read"
    return "queued"


def build_outbound_sms_request(
    *,
    account_sid: str,
    auth_token: str,
    from_number: str,
    to_number: str,
    body: str,
    base_url: str = "https://api.textgrid.com",
    status_callback_url: str | None = None,
) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/2010-04-01/Accounts/{account_sid}/Messages.json"
    token = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("utf-8")
    payload: dict[str, str] = {
        "Body": body,
        "From": from_number,
        "To": to_number,
    }
    if status_callback_url:
        payload["StatusCallback"] = status_callback_url
    return {
        "endpoint": endpoint,
        "headers": {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        "payload": payload,
    }


def verify_webhook_signature(
    *,
    secret: str,
    signature: str | None,
    request_url: str,
    payload: Mapping[str, Any],
) -> bool:
    if not signature:
        return False
    signed_data = request_url + "".join(str(payload[key]) for key in sorted(payload))
    digest = hmac.new(secret.encode("utf-8"), signed_data.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def normalize_incoming_webhook(payload: Mapping[str, Any]) -> dict[str, Any]:
    external_id = payload.get("MessageSid") or payload.get("SmsSid") or payload.get("sid")
    status = payload.get("MessageStatus") or payload.get("SmsStatus") or payload.get("status")

    metadata: dict[str, Any] = {"provider": "textgrid"}
    raw_metadata = payload.get("Metadata") or payload.get("metadata")
    if isinstance(raw_metadata, Mapping):
        metadata.update({str(key): value for key, value in raw_metadata.items() if value is not None})
    for key in ("provider_thread_id", "thread_id", "conversation_id", "business_id", "environment"):
        value = payload.get(key)
        if value is not None:
            metadata[key] = value

    if payload.get("From") and "Body" in payload:
        return {
            "content": str(payload.get("Body") or ""),
            "external_id": external_id,
            "from": payload.get("From"),
            "metadata": metadata,
            "status": "read",
            "to": payload.get("To"),
            "type": "message.inbound",
        }

    return {
        "external_id": external_id,
        "metadata": metadata,
        "status": normalize_status(None if status is None else str(status)),
        "type": "message.status",
    }
