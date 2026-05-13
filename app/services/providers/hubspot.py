from __future__ import annotations

from typing import Any, Callable

import httpx

from app.core.config import Settings, get_settings

HttpSender = Callable[..., httpx.Response]


class HubSpotProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


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
    return f"HubSpot request failed with HTTP {response.status_code}"


class HubSpotProviderClient:
    def __init__(self, *, settings: Settings | None = None, http_sender: HttpSender | None = None) -> None:
        self.settings = settings or get_settings()
        self.http_sender = http_sender or httpx.request

    def create_property(self, object_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/crm/v3/properties/{object_type}", payload)

    def update_property(self, object_type: str, property_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        update_payload = {key: value for key, value in payload.items() if key != "name"}
        return self._request("PATCH", f"/crm/v3/properties/{object_type}/{property_name}", update_payload)

    def upsert_property(self, object_type: str, property_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return {"status": "created", "property": self.create_property(object_type, payload)}
        except HubSpotProviderError as exc:
            if exc.status_code != 409:
                raise
        return {"status": "updated", "property": self.update_property(object_type, property_name, payload)}

    def create_pipeline(self, object_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/crm/v3/pipelines/{object_type}", payload)

    def list_pipelines(self, object_type: str) -> dict[str, Any]:
        return self._request("GET", f"/crm/v3/pipelines/{object_type}")

    def upsert_pipeline_by_label(self, object_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.list_pipelines(object_type)
        results = existing.get("results") if isinstance(existing, dict) else None
        if isinstance(results, list):
            for pipeline in results:
                if isinstance(pipeline, dict) and pipeline.get("label") == payload.get("label"):
                    return {"status": "exists", "pipeline": pipeline}
        return {"status": "created", "pipeline": self.create_pipeline(object_type, payload)}

    def search_objects(self, object_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/crm/v3/objects/{object_type}/search", payload)

    def create_object(self, object_type: str, properties: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/crm/v3/objects/{object_type}", {"properties": properties})

    def update_object(self, object_type: str, object_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/crm/v3/objects/{object_type}/{object_id}", {"properties": properties})

    def upsert_object_by_property(
        self,
        object_type: str,
        *,
        lookup_property: str,
        lookup_value: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        search = self.search_objects(
            object_type,
            {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": lookup_property,
                                "operator": "EQ",
                                "value": lookup_value,
                            }
                        ]
                    }
                ],
                "properties": sorted(properties.keys()),
                "limit": 1,
            },
        )
        results = search.get("results") if isinstance(search, dict) else None
        if isinstance(results, list) and results:
            object_id = str(results[0].get("id"))
            return {
                "status": "updated",
                "object": self.update_object(object_type, object_id, properties),
                "matched_by": lookup_property,
            }
        return {
            "status": "created",
            "object": self.create_object(object_type, properties),
            "matched_by": lookup_property,
        }

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.settings.hubspot_access_token:
            raise RuntimeError("HUBSPOT_ACCESS_TOKEN or HUBSPOT_PERSONAL_KEY is required")
        request_kwargs: dict[str, Any] = {
            "headers": {
                "Authorization": f"Bearer {self.settings.hubspot_access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            "timeout": self.settings.provider_request_timeout_seconds,
        }
        if payload is not None:
            request_kwargs["json"] = payload
        response = self.http_sender(
            method,
            f"{self.settings.hubspot_base_url.rstrip('/')}{path}",
            **request_kwargs,
        )
        data = _safe_json(response)
        if response.is_error:
            raise HubSpotProviderError(_extract_error(data, response), status_code=response.status_code, payload=data)
        return data
