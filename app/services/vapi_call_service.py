from __future__ import annotations

import hashlib
from typing import Any, Mapping

from app.core.config import Settings, get_settings
from app.db.client import utc_now
from app.db.provider_links import ProviderLinksRepository
from app.models.calls import VoiceOutboundCallRequest
from app.models.provider_links import ProviderObjectLink
from app.providers.vapi import (
    VapiClient,
    normalize_vapi_webhook_payload,
    verify_vapi_webhook_secret,
)


class VapiCallService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
        provider_links: ProviderLinksRepository | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.provider_links = provider_links

    def list_assistants_preview(self) -> dict[str, Any]:
        warnings = ["Phase 6 list route is config-only; no Vapi provider call was made."]
        default_id = self.settings.vapi_default_assistant_id or None
        if not default_id:
            warnings.append("No VAPI_DEFAULT_ASSISTANT_ID is configured.")
        return {
            "provider": "vapi",
            "resource": "assistants",
            "dry_run": True,
            "would_call_provider": False,
            "configured": bool(default_id),
            "default_id": default_id,
            "live_enabled": self._live_enabled(),
            "warnings": warnings,
        }

    def list_phone_numbers_preview(self) -> dict[str, Any]:
        warnings = ["Phase 6 list route is config-only; no Vapi provider call was made."]
        default_id = self.settings.vapi_default_phone_number_id or None
        if not default_id:
            warnings.append("No VAPI_DEFAULT_PHONE_NUMBER_ID is configured.")
        return {
            "provider": "vapi",
            "resource": "phone_numbers",
            "dry_run": True,
            "would_call_provider": False,
            "configured": bool(default_id),
            "default_id": default_id,
            "live_enabled": self._live_enabled(),
            "warnings": warnings,
        }

    def preview_outbound_call(self, request: VoiceOutboundCallRequest) -> dict[str, Any]:
        warnings = ["Dry-run preview only; no Vapi provider call or provider-link write was made."]
        payload = self._build_payload(request)
        return {
            "provider": "vapi",
            "dry_run": True,
            "would_call_provider": False,
            "live_applied": False,
            "action": "preview",
            "call_id": None,
            "provider_call_id": None,
            "provider_link_id": None,
            "payload": payload,
            "warnings": warnings,
            "error_message": None,
        }

    def dispatch_outbound_call(self, request: VoiceOutboundCallRequest) -> dict[str, Any]:
        self._require_dispatch_preflight(request)
        if self.client is None:
            self.client = VapiClient(api_key=self._api_key(), base_url=self.settings.vapi_base_url)
        if self.provider_links is None:
            self.provider_links = ProviderLinksRepository(settings=self.settings)

        payload = self._build_payload(request)
        ares_object_type, ares_object_id = self._ares_identity(request)
        existing_link = self.provider_links.get_by_ares_object(
            business_id=request.business_id,
            environment=request.environment,
            provider="vapi",
            ares_object_type=ares_object_type,
            ares_object_id=ares_object_id,
            provider_object_type="call",
        )
        if existing_link is not None:
            return {
                "provider": "vapi",
                "dry_run": False,
                "would_call_provider": False,
                "live_applied": False,
                "action": "skip",
                "call_id": existing_link.provider_object_id,
                "provider_call_id": existing_link.provider_object_id,
                "provider_link_id": existing_link.id,
                "payload": self._live_payload_summary(payload),
                "warnings": ["Existing Vapi call provider link found for Ares object; duplicate outbound call skipped."],
                "error_message": None,
            }

        try:
            provider_result = self.client.create_outbound_call(payload)
            provider_call_id = self._extract_provider_call_id(provider_result)
            provider_link_id = None
            action = "dispatched"
            warnings: list[str] = []
            if provider_call_id:
                link = self.provider_links.upsert_link(
                    ProviderObjectLink(
                        business_id=request.business_id,
                        environment=request.environment,
                        provider="vapi",
                        provider_object_type="call",
                        provider_object_id=provider_call_id,
                        ares_object_type=ares_object_type,
                        ares_object_id=ares_object_id,
                        sync_hash=request.sync_hash,
                        last_synced_at=utc_now(),
                        raw_payload={"source": "vapi_outbound_call_dispatch"},
                    )
                )
                provider_link_id = link.id
            else:
                action = "submitted_unlinked"
                warnings.append("Vapi response did not include a call id; provider link was not written.")
            return {
                "provider": "vapi",
                "dry_run": False,
                "would_call_provider": True,
                "live_applied": True,
                "action": action,
                "call_id": provider_call_id,
                "provider_call_id": provider_call_id,
                "provider_link_id": provider_link_id,
                "payload": self._live_payload_summary(payload),
                "warnings": warnings,
                "error_message": None,
            }
        except Exception as exc:  # noqa: BLE001
            safe_error = self._safe_error_message(exc, request=request, payload=payload)
            return {
                "provider": "vapi",
                "dry_run": False,
                "would_call_provider": True,
                "live_applied": False,
                "action": "error",
                "call_id": None,
                "provider_call_id": None,
                "provider_link_id": None,
                "payload": self._live_payload_summary(payload),
                "warnings": [],
                "error_message": safe_error,
            }

    def handle_webhook(self, payload: Mapping[str, Any], headers: Mapping[str, Any]) -> dict[str, Any]:
        provided_secret = self._header_value(headers, "x-vapi-secret")
        if self.settings.provider_webhook_signatures_required:
            if not verify_vapi_webhook_secret(self.settings.vapi_webhook_secret, provided_secret):
                return {
                    "accepted": False,
                    "event_type": None,
                    "provider_call_id": None,
                    "idempotency_key": None,
                    "trust_status": "rejected_bad_secret",
                    "status": None,
                }
            trust_status = "verified_secret"
        else:
            trust_status = "unverified_accepted"
        normalized = normalize_vapi_webhook_payload(payload)
        idempotency_key = self._idempotency_key(normalized)
        return {
            "accepted": True,
            "event_type": normalized.get("event_type"),
            "provider_call_id": normalized.get("provider_call_id"),
            "idempotency_key": idempotency_key,
            "trust_status": trust_status,
            "status": normalized.get("status"),
        }

    def _require_dispatch_preflight(self, request: VoiceOutboundCallRequest) -> None:
        if not request.operator_approval:
            raise RuntimeError("Vapi outbound call requires explicit operator approval before provider calls.")
        if not self.settings.provider_live_sends_enabled:
            raise RuntimeError("Provider live sends are disabled; set PROVIDER_LIVE_SENDS_ENABLED=true before Vapi outbound calls.")
        if not self.settings.vapi_provider_live_sends_enabled:
            raise RuntimeError("Vapi live sends are disabled; set VAPI_PROVIDER_LIVE_SENDS_ENABLED=true before outbound calls.")
        if not self._api_key():
            raise RuntimeError("Vapi API key/private key is required before live outbound calls.")
        if not (request.assistant_id or self.settings.vapi_default_assistant_id):
            raise RuntimeError("Vapi assistant ID is required before live outbound calls.")
        if not (request.phone_number_id or self.settings.vapi_default_phone_number_id):
            raise RuntimeError("Vapi phone number ID is required before live outbound calls.")
        if not request.to_number.strip():
            raise RuntimeError("Vapi outbound call requires to_number.")

    def _build_payload(self, request: VoiceOutboundCallRequest) -> dict[str, Any]:
        metadata = {
            **dict(request.metadata or {}),
            "business_id": request.business_id,
            "environment": request.environment,
        }
        for key in ("crm_record_id", "opportunity_id", "task_id", "sync_hash"):
            value = getattr(request, key)
            if value not in (None, ""):
                metadata[key] = value
        payload: dict[str, Any] = {
            "assistantId": request.assistant_id or self.settings.vapi_default_assistant_id or None,
            "phoneNumberId": request.phone_number_id or self.settings.vapi_default_phone_number_id or None,
            "customer": {"number": request.to_number},
            "metadata": {key: value for key, value in metadata.items() if value not in (None, "")},
        }
        if request.customer_name:
            payload["customer"]["name"] = request.customer_name
        if request.from_number:
            payload["fromNumber"] = request.from_number
        return {key: value for key, value in payload.items() if value not in (None, "")}

    @staticmethod
    def _live_payload_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
        customer = payload.get("customer") if isinstance(payload.get("customer"), Mapping) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
        return {
            "redacted": True,
            "assistant_id_present": bool(payload.get("assistantId")),
            "phone_number_id_present": bool(payload.get("phoneNumberId")),
            "customer_number_present": bool(customer.get("number")),
            "customer_name_present": bool(customer.get("name")),
            "from_number_present": bool(payload.get("fromNumber")),
            "metadata_field_count": len(metadata),
        }

    def _api_key(self) -> str:
        return self.settings.vapi_api_key or self.settings.vapi_private_key or ""

    def _live_enabled(self) -> bool:
        return bool(self.settings.provider_live_sends_enabled and self.settings.vapi_provider_live_sends_enabled and self._api_key())

    @staticmethod
    def _ares_identity(request: VoiceOutboundCallRequest) -> tuple[str, str]:
        if request.crm_record_id:
            return "crm_record", request.crm_record_id
        if request.opportunity_id:
            return "opportunity", request.opportunity_id
        if request.task_id:
            return "task", request.task_id
        stable = hashlib.sha256(
            "|".join(
                [
                    request.business_id,
                    request.environment,
                    request.to_number,
                    request.assistant_id or "",
                    request.phone_number_id or "",
                    request.sync_hash or "",
                ]
            ).encode("utf-8")
        ).hexdigest()[:24]
        return "voice_call_request", f"vcr_{stable}"

    @staticmethod
    def _extract_provider_call_id(provider_result: Any) -> str | None:
        if not isinstance(provider_result, Mapping):
            return None
        for key in ("id", "callId", "call_id", "provider_call_id"):
            value = provider_result.get(key)
            if value not in (None, ""):
                return str(value)
        call = provider_result.get("call")
        if isinstance(call, Mapping):
            for key in ("id", "callId", "call_id"):
                value = call.get(key)
                if value not in (None, ""):
                    return str(value)
        return None

    @staticmethod
    def _header_value(headers: Mapping[str, Any], name: str) -> str | None:
        for key, value in headers.items():
            if str(key).casefold() == name.casefold():
                return str(value)
        return None

    @staticmethod
    def _idempotency_key(normalized: Mapping[str, Any]) -> str:
        base = "|".join(
            str(normalized.get(key) or "")
            for key in ("event_type", "provider_call_id", "timestamp", "message_id")
        )
        return "vapi_webhook_" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]

    def _safe_error_message(
        self,
        exc: Exception,
        *,
        request: VoiceOutboundCallRequest | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> str:
        _ = (exc, request, payload)
        return "Vapi provider dispatch failed."
