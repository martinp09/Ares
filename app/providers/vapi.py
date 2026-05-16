from __future__ import annotations

import hmac
import json
import re
from http import HTTPStatus
from typing import Any, Callable, Mapping
from urllib import error, parse, request

from app.models.providers import ProviderTransportError
from app.services.provider_retry_service import ProviderRetryService

_DEFAULT_BASE_URL = "https://api.vapi.ai"
_DEFAULT_USER_AGENT = "Mozilla/5.0 Ares/1.0 VapiClient"
_SANITIZED_ERROR_LIMIT = 240
_SAFE_RESPONSE_HEADER_NAMES = {"retry-after"}
_SAFE_RESPONSE_HEADER_VALUE_LIMIT = 120
_SENSITIVE_HEADER_MARKERS = ("authorization", "auth", "bearer", "token", "secret", "cookie", "key", "vapi")

RequestSender = Callable[[dict[str, Any]], Any]


def _masked_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def build_vapi_request(
    *,
    api_key: str,
    method: str,
    path: str,
    payload: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
    base_url: str = _DEFAULT_BASE_URL,
) -> dict[str, Any]:
    normalized_path = path if path.startswith("/") else f"/{path}"
    endpoint = f"{base_url.rstrip('/')}{normalized_path}"
    if query:
        encoded = parse.urlencode({key: value for key, value in query.items() if value is not None}, doseq=True)
        if encoded:
            endpoint = f"{endpoint}?{encoded}"
    return {
        "method": method.upper(),
        "endpoint": endpoint,
        "headers": {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": _DEFAULT_USER_AGENT,
        },
        "payload": dict(payload or {}),
    }


def _sanitized_transport_message(method: str, path: str, *, status_code: int | None = None, reason: str | None = None) -> str:
    parts = [f"Vapi transport failed for {method.upper()} {path}"]
    if status_code is not None:
        try:
            status_label = HTTPStatus(status_code).phrase
        except ValueError:
            status_label = "HTTP error"
        parts.append(f"status={status_code} {status_label}")
    if reason:
        safe_reason = reason.replace("\n", " ").replace("\r", " ")[:_SANITIZED_ERROR_LIMIT]
        safe_reason = _redact_sensitive_text(safe_reason)
        parts.append(f"reason={safe_reason}")
    return "; ".join(parts)


def _redact_sensitive_text(message: str, known_secrets: tuple[str, ...] = ()) -> str:
    redactions = [
        (r"(?i)(authorization\s*[:=]\s*)bearer\s+[^\s,;]+", r"\1Bearer [redacted]"),
        (r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]"),
        (r"(?i)([?&](?:access_token|token|api[_-]?key|secret|password|private_key)=)[^&\s]+", r"\1[redacted]"),
        (r"(?i)\b(token|api[_-]?key|secret|password|private[_-]?key)\b\s*[:=]\s*[^\s,;]+", r"\1=[redacted]"),
        (r"(?i)(vapi[_-]?(?:api|private|public)?[_-]?key\s*)[^\s,;]+", r"\1[redacted]"),
    ]
    for pattern, replacement in redactions:
        message = re.sub(pattern, replacement, message)
    for secret in known_secrets:
        if secret:
            message = message.replace(secret, "[redacted]")
    return message[:_SANITIZED_ERROR_LIMIT]


def _sanitize_transport_headers(headers: Mapping[str, Any] | None) -> dict[str, str]:
    safe_headers: dict[str, str] = {}
    for name, value in (headers or {}).items():
        normalized_name = str(name).strip()
        lower_name = normalized_name.lower()
        if lower_name not in _SAFE_RESPONSE_HEADER_NAMES:
            continue
        if any(marker in lower_name for marker in _SENSITIVE_HEADER_MARKERS):
            continue
        safe_value = str(value).replace("\n", " ").replace("\r", " ").strip()[:_SAFE_RESPONSE_HEADER_VALUE_LIMIT]
        if any(marker in safe_value.lower() for marker in _SENSITIVE_HEADER_MARKERS):
            continue
        safe_headers[normalized_name] = safe_value
    return safe_headers


def sanitize_provider_transport_error(
    exc: ProviderTransportError,
    method: str = "REQUEST",
    path: str = "/",
    *,
    known_secrets: tuple[str, ...] = (),
) -> ProviderTransportError:
    return ProviderTransportError(
        _redact_sensitive_text(
            _sanitized_transport_message(method, path, status_code=exc.status_code, reason=str(exc)),
            known_secrets=known_secrets,
        ),
        status_code=exc.status_code,
        headers=_sanitize_transport_headers(exc.headers),
    )


class VapiClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        request_sender: RequestSender | None = None,
        retry_service: ProviderRetryService | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.request_sender = request_sender or self._default_request_sender
        self.retry_service = retry_service or ProviderRetryService()
        self.timeout_seconds = max(0.1, timeout_seconds)

    def __repr__(self) -> str:
        return f"VapiClient(base_url='{self.base_url}', api_key='{_masked_secret(self.api_key)}')"

    def list_assistants(self) -> dict[str, Any]:
        return self._send("GET", "/assistant")

    def list_phone_numbers(self) -> dict[str, Any]:
        return self._send("GET", "/phone-number")

    def create_outbound_call(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/call", payload=payload)

    def get_call(self, call_id: str) -> dict[str, Any]:
        return self._send("GET", f"/call/{parse.quote(str(call_id), safe='')}")

    def _send(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        query: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        outbound_request = build_vapi_request(
            api_key=self.api_key,
            method=method,
            path=path,
            payload=payload,
            query=query,
            base_url=self.base_url,
        )
        attempt = 0
        while True:
            attempt += 1
            try:
                raw_response = self.request_sender(outbound_request)
                if raw_response is None:
                    return {}
                if isinstance(raw_response, dict):
                    return raw_response
                if isinstance(raw_response, list):
                    return {"results": raw_response}
                raise ProviderTransportError(f"Vapi transport returned unsupported response type for {method.upper()} {path}")
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, ProviderTransportError):
                    safe_exc = sanitize_provider_transport_error(exc, method, path, known_secrets=(self.api_key,))
                else:
                    safe_exc = ProviderTransportError(_sanitized_transport_message(method, path, reason=exc.__class__.__name__))
                retry_state = self.retry_service.evaluate(attempt, safe_exc)
                if retry_state.exhausted:
                    raise safe_exc
                self.retry_service.sleep(self._retry_delay_seconds(safe_exc, retry_state.next_delay_seconds))

    def _default_request_sender(self, outbound_request: dict[str, Any]) -> dict[str, Any]:
        payload = outbound_request.get("payload") or {}
        body = json.dumps(payload).encode("utf-8") if payload and outbound_request.get("method") not in {"GET", "HEAD"} else None
        req = request.Request(
            outbound_request["endpoint"],
            data=body,
            headers=outbound_request.get("headers") or {},
            method=outbound_request.get("method") or "GET",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            raise ProviderTransportError(
                _sanitized_transport_message(req.get_method(), parse.urlsplit(req.full_url).path or "/", status_code=exc.code),
                status_code=exc.code,
                headers=_sanitize_transport_headers(exc.headers),
            ) from exc
        except error.URLError as exc:
            raise ProviderTransportError(
                _sanitized_transport_message(req.get_method(), parse.urlsplit(req.full_url).path or "/", reason=exc.reason.__class__.__name__),
            ) from exc

    @staticmethod
    def _retry_delay_seconds(exc: ProviderTransportError, fallback_delay: float | None) -> float:
        retry_after = None
        for name, value in (exc.headers or {}).items():
            if str(name).strip().lower() == "retry-after":
                retry_after = value
                break
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                return max(0.0, fallback_delay or 0.0)
        return max(0.0, fallback_delay or 0.0)


def verify_vapi_webhook_secret(expected: str | None, provided: str | None) -> bool:
    if not expected or not provided:
        return False
    return hmac.compare_digest(str(expected), str(provided))


def normalize_vapi_webhook_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    message = payload.get("message") if isinstance(payload.get("message"), Mapping) else {}
    call = payload.get("call") if isinstance(payload.get("call"), Mapping) else {}
    message_call = message.get("call") if isinstance(message.get("call"), Mapping) else {}
    artifact = payload.get("artifact") if isinstance(payload.get("artifact"), Mapping) else {}
    message_artifact = message.get("artifact") if isinstance(message.get("artifact"), Mapping) else {}
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), Mapping) else {}
    message_analysis = message.get("analysis") if isinstance(message.get("analysis"), Mapping) else {}
    artifact_recording = artifact.get("recording") if isinstance(artifact.get("recording"), Mapping) else {}
    message_artifact_recording = message_artifact.get("recording") if isinstance(message_artifact.get("recording"), Mapping) else {}

    event_type = str(payload.get("type") or payload.get("event") or message.get("type") or "vapi.webhook").strip()
    provider_call_id = _first_present(
        payload.get("callId"),
        payload.get("call_id"),
        call.get("id"),
        call.get("callId"),
        message_call.get("id"),
        message_call.get("callId"),
        message.get("callId"),
        message.get("call_id"),
    )
    status = _first_present(
        payload.get("status"),
        call.get("status"),
        message_call.get("status"),
        message.get("status"),
        message.get("endedReason"),
    )
    transcript = _first_present(
        payload.get("transcript"),
        artifact.get("transcript"),
        message_artifact.get("transcript"),
        call.get("transcript"),
        message_call.get("transcript"),
        message.get("transcript"),
    )
    summary = _first_present(
        payload.get("summary"),
        analysis.get("summary"),
        message_analysis.get("summary"),
        artifact.get("summary"),
        message_artifact.get("summary"),
        message.get("summary"),
    )
    recording_url = _first_present(
        payload.get("recordingUrl"),
        payload.get("recording_url"),
        message.get("recordingUrl"),
        message.get("recording_url"),
        message.get("stereoRecordingUrl"),
        message.get("stereo_recording_url"),
        message.get("videoUrl"),
        message.get("video_url"),
        artifact.get("recordingUrl"),
        artifact.get("recording_url"),
        message_artifact.get("recordingUrl"),
        message_artifact.get("recording_url"),
        _recording_url_from_recording(artifact_recording),
        _recording_url_from_recording(message_artifact_recording),
        call.get("recordingUrl"),
        call.get("recording_url"),
        message_call.get("recordingUrl"),
        message_call.get("recording_url"),
    )
    timestamp = _first_present(payload.get("timestamp"), payload.get("createdAt"), message.get("timestamp"), message.get("createdAt"))
    message_id = _first_present(payload.get("id"), payload.get("messageId"), message.get("id"), message.get("messageId"))

    raw_payload = {
        key: value
        for key, value in {
            "type": payload.get("type"),
            "event": payload.get("event"),
            "status": status,
            "timestamp": timestamp,
            "message_id": message_id,
            "call_id_present": bool(provider_call_id),
        }.items()
        if value not in (None, "")
    }
    return {
        "event_type": event_type,
        "provider_call_id": str(provider_call_id) if provider_call_id is not None else None,
        "status": str(status) if status is not None else None,
        "transcript": str(transcript) if transcript is not None else None,
        "summary": str(summary) if summary is not None else None,
        "recording_url": str(recording_url) if recording_url is not None else None,
        "timestamp": str(timestamp) if timestamp is not None else None,
        "message_id": str(message_id) if message_id is not None else None,
        "raw_payload": raw_payload,
    }


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _recording_url_from_recording(recording: Mapping[str, Any]) -> Any:
    nested_mono = recording.get("mono") if isinstance(recording.get("mono"), Mapping) else {}
    nested_stereo = recording.get("stereo") if isinstance(recording.get("stereo"), Mapping) else {}
    nested_video = recording.get("video") if isinstance(recording.get("video"), Mapping) else {}
    return _first_present(
        recording.get("url"),
        recording.get("recordingUrl"),
        recording.get("recording_url"),
        recording.get("stereoUrl"),
        recording.get("stereoRecordingUrl"),
        recording.get("stereo_recording_url"),
        recording.get("videoUrl"),
        recording.get("videoRecordingUrl"),
        recording.get("video_recording_url"),
        recording.get("combinedUrl"),
        recording.get("combined_url"),
        nested_mono.get("combinedUrl"),
        nested_mono.get("combined_url"),
        nested_mono.get("url"),
        nested_mono.get("recordingUrl"),
        nested_mono.get("recording_url"),
        nested_stereo.get("combinedUrl"),
        nested_stereo.get("combined_url"),
        nested_stereo.get("url"),
        nested_stereo.get("recordingUrl"),
        nested_stereo.get("recording_url"),
        nested_video.get("combinedUrl"),
        nested_video.get("combined_url"),
        nested_video.get("url"),
        nested_video.get("recordingUrl"),
        nested_video.get("recording_url"),
    )
