#!/usr/bin/env python3
"""Local TextGrid SMS reply-agent ingest smoke.

This script posts one Twilio-compatible form webhook into Ares and optionally
drains the protected pending-job processor. It never calls TextGrid directly.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import sys
import uuid
from typing import Any, Mapping
from urllib import error, request
from urllib.parse import urlencode


WEBHOOK_PATH = "/sms-agent/webhooks/textgrid"
PROCESS_PENDING_PATH = "/sms-agent/internal/process-pending"


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def build_twilio_signature(*, secret: str, request_url: str, payload: Mapping[str, Any]) -> str:
    signed_data = request_url + "".join(str(payload[key]) for key in sorted(payload))
    digest = hmac.new(secret.encode("utf-8"), signed_data.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def _post_form(
    *,
    url: str,
    payload: Mapping[str, str],
    signature: str,
    timeout: int,
) -> dict[str, Any]:
    body = urlencode(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Twilio-Signature": signature,
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            status_code = getattr(response, "status", response.getcode())
            headers = dict(response.headers.items()) if hasattr(response.headers, "items") else {}
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"webhook smoke failed: HTTP {exc.code} {response_body}") from exc
    if status_code != 200:
        raise RuntimeError(f"webhook smoke failed: HTTP {status_code} {response_body}")
    return {
        "status_code": status_code,
        "content_type": headers.get("Content-Type") or headers.get("content-type"),
        "ares_status": headers.get("X-Ares-Sms-Agent-Status") or headers.get("x-ares-sms-agent-status"),
        "body_bytes": len(response_body.encode("utf-8")),
    }


def _post_json(
    *,
    url: str,
    payload: Mapping[str, Any],
    runtime_api_key: str,
    timeout: int,
) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {runtime_api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            status_code = getattr(response, "status", response.getcode())
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"process-pending smoke failed: HTTP {exc.code} {response_body}") from exc
    if status_code != 200:
        raise RuntimeError(f"process-pending smoke failed: HTTP {status_code} {response_body}")
    try:
        parsed = json.loads(response_body) if response_body else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"process-pending smoke returned non-JSON body: {response_body}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("process-pending smoke returned non-object JSON")
    return {"status_code": status_code, "response": parsed}


def _mask_phone(value: str) -> str:
    if not value.startswith("+") or len(value) < 8:
        return value
    return f"{value[:2]}{'*' * max(len(value) - 6, 0)}{value[-4:]}"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if isinstance(item, str) and any(
                token in lowered for token in ("secret", "token", "api_key", "authorization", "signature")
            ):
                sanitized[str(key)] = "<redacted>"
            else:
                sanitized[str(key)] = _sanitize(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return _mask_phone(value)
    return value


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    runtime_url = args.runtime_url.rstrip("/")
    webhook_url = _join_url(runtime_url, WEBHOOK_PATH)
    process_pending_url = _join_url(runtime_url, PROCESS_PENDING_PATH)
    message_sid = args.message_sid or f"SM{uuid.uuid4().hex}"
    form_payload = {
        "MessageSid": message_sid,
        "SmsSid": message_sid,
        "SmsMessageSid": message_sid,
        "AccountSid": "ACareslocalsmoke",
        "MessagingServiceSid": "MGareslocalsmoke",
        "From": args.from_number,
        "To": args.to,
        "Body": args.body,
        "NumMedia": "0",
    }
    signature = build_twilio_signature(
        secret=args.webhook_secret,
        request_url=webhook_url,
        payload=form_payload,
    )
    webhook = _post_form(
        url=webhook_url,
        payload=form_payload,
        signature=signature,
        timeout=args.timeout,
    )
    process_pending = None
    if args.runtime_api_key:
        process_pending = _post_json(
            url=process_pending_url,
            payload={"limit": args.process_limit},
            runtime_api_key=args.runtime_api_key,
            timeout=args.timeout,
        )
    result = {
        "status": "passed",
        "runtime_url": runtime_url,
        "webhook": webhook,
        "process_pending": process_pending or {"skipped": True},
        "request": {
            "webhook_path": WEBHOOK_PATH,
            "process_pending_path": PROCESS_PENDING_PATH,
            "message_sid": message_sid,
            "from": args.from_number,
            "to": args.to,
            "body_chars": len(args.body),
            "signed_header": "X-Twilio-Signature",
            "authorization_sent_to_webhook": False,
            "live_textgrid_send": False,
            "provider_dashboard_mutation": False,
        },
    }
    return _sanitize(result)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-url", required=True)
    parser.add_argument("--webhook-secret", required=True)
    parser.add_argument("--from", dest="from_number", required=True)
    parser.add_argument("--to", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--runtime-api-key")
    parser.add_argument("--message-sid")
    parser.add_argument("--process-limit", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=15)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = run_smoke(parse_args(argv))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
