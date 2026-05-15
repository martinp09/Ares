from __future__ import annotations

import json
from typing import Any, Callable, Mapping
from urllib import error, parse, request

from app.models.providers import ProviderTransportError
from app.services.provider_retry_service import ProviderRetryService

_DEFAULT_BASE_URL = "https://tracerfy.com/v1/api"
_DEFAULT_USER_AGENT = "Mozilla/5.0 Ares/1.0 TracerfyClient"

RequestSender = Callable[[dict[str, Any]], Any]


def _masked_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def build_tracerfy_request(
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


def primary_phone_from_trace(response: Mapping[str, Any]) -> str | None:
    for person in response.get("persons") or []:
        if not isinstance(person, Mapping) or person.get("deceased") is True:
            continue
        phones = person.get("phones") or []
        ranked = sorted(
            [phone for phone in phones if isinstance(phone, Mapping) and str(phone.get("number") or "").strip()],
            key=lambda phone: int(phone.get("rank") or 999),
        )
        for phone in ranked:
            if phone.get("dnc") is True:
                continue
            return str(phone.get("number") or "").strip()
        if ranked:
            return str(ranked[0].get("number") or "").strip()
    return None


def primary_email_from_trace(response: Mapping[str, Any]) -> str | None:
    for person in response.get("persons") or []:
        if not isinstance(person, Mapping) or person.get("deceased") is True:
            continue
        emails = person.get("emails") or []
        ranked = sorted(
            [email for email in emails if isinstance(email, Mapping) and str(email.get("email") or "").strip()],
            key=lambda email: int(email.get("rank") or 999),
        )
        if ranked:
            return str(ranked[0].get("email") or "").strip()
    return None


class TracerfyClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        request_sender: RequestSender | None = None,
        retry_service: ProviderRetryService | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.request_sender = request_sender or self._default_request_sender
        self.retry_service = retry_service or ProviderRetryService()

    def __repr__(self) -> str:
        return f"TracerfyClient(base_url='{self.base_url}', api_key='{_masked_secret(self.api_key)}')"

    def instant_address_lookup(
        self,
        *,
        address: str,
        city: str,
        state: str,
        zip_code: str | None = None,
        find_owner: bool = True,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "address": address,
            "city": city,
            "state": state,
            "find_owner": find_owner,
        }
        if zip_code:
            payload["zip"] = zip_code
        if not find_owner:
            payload["first_name"] = first_name
            payload["last_name"] = last_name
        return self._send("POST", "/trace/lookup/", payload=payload)

    def instant_apn_lookup(self, *, parcel_id: str, county: str, state: str) -> dict[str, Any]:
        return self._send("POST", "/trace/parcel/lookup/", payload={"parcel_id": parcel_id, "county": county, "state": state})

    def dnc_lookup(self, *, phone: str) -> dict[str, Any]:
        return self._send("POST", "/dnc/lookup/", payload={"phone": phone})

    def list_queues(self, *, page: int | None = None) -> Any:
        return self._send("GET", "/queues/", query={"page": page})

    def get_queue(self, queue_id: int | str) -> Any:
        return self._send("GET", f"/queue/{queue_id}")

    def address_autocomplete(self, *, search: str) -> dict[str, Any]:
        return self._send("POST", "/lead-builder/autocomplete/", payload={"search": search})

    def _send(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        query: Mapping[str, Any] | None = None,
    ) -> Any:
        outbound_request = build_tracerfy_request(
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
                if isinstance(raw_response, (dict, list)):
                    return raw_response
                raise ProviderTransportError(
                    f"Tracerfy transport returned unsupported response type for {method.upper()} {path}",
                )
            except Exception as exc:  # noqa: BLE001
                if not isinstance(exc, ProviderTransportError):
                    exc = ProviderTransportError(f"Tracerfy transport failed for {method.upper()} {path}: {exc}")
                retry_state = self.retry_service.evaluate(attempt, exc)
                if retry_state.exhausted:
                    raise exc
                self.retry_service.sleep(retry_state.next_delay_seconds or 0.0)

    @staticmethod
    def _default_request_sender(outbound_request: dict[str, Any]) -> Any:
        data = None
        if outbound_request.get("method") not in {"GET", "HEAD"}:
            data = json.dumps(outbound_request.get("payload") or {}).encode("utf-8")
        req = request.Request(
            outbound_request["endpoint"],
            data=data,
            headers=outbound_request["headers"],
            method=outbound_request["method"],
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ProviderTransportError(
                f"Tracerfy request failed with HTTP {exc.code}: {body}", status_code=exc.code, response_body=body
            ) from exc
        except error.URLError as exc:
            raise ProviderTransportError(f"Tracerfy request failed: {exc.reason}") from exc
