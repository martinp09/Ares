import hashlib
import hmac
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse


def verify_webhook_signature(secret: str, signature: str | None, raw_body: bytes) -> bool:
    if not signature:
        return False
    expected_digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    candidate = signature.strip()
    if candidate.startswith("sha256="):
        candidate = candidate[7:]
    return hmac.compare_digest(expected_digest, candidate)


def normalize_booking_webhook(payload: Mapping[str, Any]) -> dict[str, Any]:
    trigger_event = str(payload.get("triggerEvent") or payload.get("event") or "").upper()
    body = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else {}
    booking = body.get("booking") if isinstance(body, Mapping) and isinstance(body.get("booking"), Mapping) else {}
    metadata = booking.get("metadata") if isinstance(booking.get("metadata"), Mapping) else {}

    event_type_map = {
        "BOOKING_CREATED": "booking.created",
        "BOOKING_RESCHEDULED": "booking.rescheduled",
        "BOOKING_CANCELLED": "booking.cancelled",
    }
    booking_status_map = {
        "BOOKING_CREATED": "booked",
        "BOOKING_RESCHEDULED": "rescheduled",
        "BOOKING_CANCELLED": "cancelled",
    }

    booking_url = str(booking.get("bookingUrl") or booking.get("url") or "")
    lead_id = metadata.get("lead_id")
    if not lead_id and booking_url:
        parsed = urlparse(booking_url)
        lead_id = parse_qs(parsed.query).get("lead_id", [None])[0]

    return {
        "provider": "cal.com",
        "event_type": event_type_map.get(trigger_event, "booking.unknown"),
        "booking_status": booking_status_map.get(trigger_event, "pending"),
        "external_booking_id": booking.get("uid") or booking.get("id"),
        "starts_at": booking.get("startTime"),
        "lead_id": lead_id,
        "metadata": {"provider": "cal.com", "raw_event": payload},
    }
