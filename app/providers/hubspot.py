from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any, Callable, Mapping
from urllib import error, parse, request

from app.models.providers import ProviderTransportError
from app.services.provider_retry_service import ProviderRetryService

_DEFAULT_BASE_URL = "https://api.hubapi.com"
_DEFAULT_USER_AGENT = "Mozilla/5.0 Ares/1.0 HubSpotClient"
_SANITIZED_ERROR_LIMIT = 240
_SAFE_RESPONSE_HEADER_NAMES = {"retry-after"}
_SAFE_RESPONSE_HEADER_PREFIXES = ("x-ratelimit-",)
_SAFE_RESPONSE_HEADER_VALUE_LIMIT = 120
_SENSITIVE_HEADER_MARKERS = ("authorization", "auth", "bearer", "token", "secret", "cookie", "key")

RequestSender = Callable[[dict[str, Any]], Any]


def _masked_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def build_hubspot_request(
    *,
    access_token: str,
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
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": _DEFAULT_USER_AGENT,
        },
        "payload": dict(payload or {}),
    }


def _sanitized_transport_message(method: str, path: str, *, status_code: int | None = None, reason: str | None = None) -> str:
    parts = [f"HubSpot transport failed for {method.upper()} {path}"]
    if status_code is not None:
        try:
            status_label = HTTPStatus(status_code).phrase
        except ValueError:
            status_label = "HTTP error"
        parts.append(f"status={status_code} {status_label}")
    if reason:
        safe_reason = reason.replace("\n", " ").replace("\r", " ")[:_SANITIZED_ERROR_LIMIT]
        parts.append(f"reason={safe_reason}")
    return "; ".join(parts)


def _sanitize_transport_headers(headers: Mapping[str, Any] | None) -> dict[str, str]:
    safe_headers: dict[str, str] = {}
    for name, value in (headers or {}).items():
        normalized_name = str(name).strip()
        lower_name = normalized_name.lower()
        if lower_name not in _SAFE_RESPONSE_HEADER_NAMES and not lower_name.startswith(_SAFE_RESPONSE_HEADER_PREFIXES):
            continue
        if any(marker in lower_name for marker in _SENSITIVE_HEADER_MARKERS):
            continue
        safe_value = str(value).replace("\n", " ").replace("\r", " ").strip()[:_SAFE_RESPONSE_HEADER_VALUE_LIMIT]
        if any(marker in safe_value.lower() for marker in _SENSITIVE_HEADER_MARKERS):
            continue
        safe_headers[normalized_name] = safe_value
    return safe_headers


def _sanitize_provider_transport_error(exc: ProviderTransportError, method: str, path: str) -> ProviderTransportError:
    return ProviderTransportError(
        _sanitized_transport_message(method, path, status_code=exc.status_code),
        status_code=exc.status_code,
        headers=_sanitize_transport_headers(exc.headers),
    )


class HubSpotClient:
    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = _DEFAULT_BASE_URL,
        request_sender: RequestSender | None = None,
        retry_service: ProviderRetryService | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.request_sender = request_sender or self._default_request_sender
        self.retry_service = retry_service or ProviderRetryService()
        self.timeout_seconds = max(0.1, timeout_seconds)

    def __repr__(self) -> str:
        return f"HubSpotClient(base_url='{self.base_url}', access_token='{_masked_secret(self.access_token)}')"

    def list_owners(self, **query: Any) -> dict[str, Any]:
        return self._send("GET", "/crm/v3/owners", query=query)

    def list_properties(self, object_type: str) -> dict[str, Any]:
        return self._send("GET", f"/crm/v3/properties/{object_type}")

    def list_property_groups(self, object_type: str) -> dict[str, Any]:
        return self._send("GET", f"/crm/v3/properties/{object_type}/groups")

    def list_pipelines(self, object_type: str = "deals") -> dict[str, Any]:
        return self._send("GET", f"/crm/v3/pipelines/{object_type}")

    def create_property_group(self, object_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", f"/crm/v3/properties/{object_type}/groups", payload=payload)

    def create_property(self, object_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", f"/crm/v3/properties/{object_type}", payload=payload)

    def create_pipeline(self, object_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", f"/crm/v3/pipelines/{object_type}", payload=payload)

    def create_pipeline_stage(self, object_type: str, pipeline_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", f"/crm/v3/pipelines/{object_type}/{pipeline_id}/stages", payload=payload)

    def create_object(self, object_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", f"/crm/v3/objects/{object_type}", payload=payload)

    def update_object(self, object_type: str, record_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("PATCH", f"/crm/v3/objects/{object_type}/{record_id}", payload=payload)

    def _send(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        query: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        outbound_request = build_hubspot_request(
            access_token=self.access_token,
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
                raise ProviderTransportError(
                    f"HubSpot transport returned unsupported response type for {method.upper()} {path}",
                )
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, ProviderTransportError):
                    exc = _sanitize_provider_transport_error(exc, method, path)
                else:
                    exc = ProviderTransportError(
                        _sanitized_transport_message(method, path, reason=exc.__class__.__name__),
                    )
                retry_state = self.retry_service.evaluate(attempt, exc)
                if retry_state.exhausted:
                    raise exc
                self.retry_service.sleep(self._retry_delay_seconds(exc, retry_state.next_delay_seconds))

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
