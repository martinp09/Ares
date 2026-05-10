from __future__ import annotations

from typing import Any, Callable

import httpx

from app.core.config import Settings, get_settings

HttpSender = Callable[..., httpx.Response]


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {"message": response.text}
    return payload if isinstance(payload, dict) else {"data": payload}


def _extract_error(payload: dict[str, Any], response: httpx.Response) -> str:
    for key in ("message", "error", "detail", "description"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if response.text.strip():
        return response.text.strip()
    return f"Vapi request failed with HTTP {response.status_code}"


class VapiProviderClient:
    def __init__(self, *, settings: Settings | None = None, http_sender: HttpSender | None = None) -> None:
        self.settings = settings or get_settings()
        self.http_sender = http_sender or httpx.request

    def create_assistant(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/assistant", payload)

    def create_phone_number(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/phone-number", payload)

    def update_phone_number(self, phone_number_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/phone-number/{phone_number_id}", payload)

    def create_call(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/call", payload)

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.vapi_api_key:
            raise RuntimeError("VAPI_API_KEY is required")
        response = self.http_sender(
            method,
            f"{self.settings.vapi_base_url.rstrip('/')}{path}",
            headers={
                "Authorization": f"Bearer {self.settings.vapi_api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.settings.provider_request_timeout_seconds,
        )
        data = _safe_json(response)
        if response.is_error:
            raise RuntimeError(_extract_error(data, response))
        return data
