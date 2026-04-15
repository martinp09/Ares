import hashlib
import hmac
import json

from app.providers.calcom import normalize_booking_webhook, verify_webhook_signature


def _sha256_signature(secret: str, raw_body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_calcom_webhook_signature_validation() -> None:
    payload = {"triggerEvent": "BOOKING_CREATED", "payload": {"booking": {"uid": "abc"}}}
    raw_body = json.dumps(payload).encode("utf-8")
    signature = _sha256_signature("cal_whsec_1", raw_body)

    assert verify_webhook_signature("cal_whsec_1", signature, raw_body)
    assert not verify_webhook_signature("cal_whsec_1", "sha256=bad", raw_body)


def test_calcom_booking_created_normalization_prefers_metadata_lead_id() -> None:
    normalized = normalize_booking_webhook(
        {
            "triggerEvent": "BOOKING_CREATED",
            "payload": {
                "booking": {
                    "uid": "book_123",
                    "startTime": "2026-04-14T17:00:00.000Z",
                    "metadata": {"lead_id": "lead_meta_1"},
                    "responses": {"notes": "Please call first"},
                }
            },
        }
    )

    assert normalized["event_type"] == "booking.created"
    assert normalized["booking_status"] == "booked"
    assert normalized["external_booking_id"] == "book_123"
    assert normalized["lead_id"] == "lead_meta_1"


def test_calcom_booking_cancelled_normalization_extracts_lead_id_from_url() -> None:
    normalized = normalize_booking_webhook(
        {
            "triggerEvent": "BOOKING_CANCELLED",
            "payload": {
                "booking": {
                    "uid": "book_456",
                    "startTime": "2026-04-15T17:00:00.000Z",
                    "metadata": {},
                    "bookingUrl": "https://cal.com/lease-option/call?lead_id=lead_query_2",
                }
            },
        }
    )

    assert normalized["event_type"] == "booking.cancelled"
    assert normalized["booking_status"] == "cancelled"
    assert normalized["lead_id"] == "lead_query_2"
