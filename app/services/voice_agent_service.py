from __future__ import annotations

import json
from typing import Any

from app.core.config import Settings, get_settings
from app.models.voice_agents import (
    VapiWebhookResponse,
    VoiceAssistantCreateRequest,
    VoiceOutboundCallRequest,
    VoicePhoneNumberCreateRequest,
    VoiceProviderActionResponse,
)
from app.providers.textgrid import normalize_phone_number
from app.services.providers.vapi import VapiProviderClient


class VoiceAgentService:
    def __init__(self, *, settings: Settings | None = None, vapi_client: VapiProviderClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.vapi_client = vapi_client or VapiProviderClient(settings=self.settings)

    def create_assistant(self, request: VoiceAssistantCreateRequest) -> VoiceProviderActionResponse:
        payload = self.build_assistant_payload(
            name=request.name,
            first_message=request.first_message,
            system_prompt=request.system_prompt,
            server_url=request.server_url,
            model_provider=request.model_provider,
            model=request.model,
            voice_provider=request.voice_provider,
            voice_id=request.voice_id,
            metadata=request.metadata,
        )
        if request.dry_run_only or not self._vapi_config_changes_enabled():
            return VoiceProviderActionResponse(
                action="create_assistant",
                status="skipped",
                dry_run=True,
                request_payload=payload,
            )
        response = self.vapi_client.create_assistant(payload)
        return VoiceProviderActionResponse(
            action="create_assistant",
            status="created",
            dry_run=False,
            provider_id=_extract_vapi_id(response),
            request_payload=payload,
            provider_response=response,
        )

    def create_phone_number(self, request: VoicePhoneNumberCreateRequest) -> VoiceProviderActionResponse:
        payload: dict[str, Any] = {
            "provider": "vapi",
            "name": request.name,
        }
        assistant_id = request.assistant_id or self.settings.vapi_default_assistant_id
        if assistant_id:
            payload["assistantId"] = assistant_id
        if request.number_desired_area_code:
            payload["numberDesiredAreaCode"] = request.number_desired_area_code
        server_url = request.server_url or self.settings.vapi_webhook_url
        if server_url:
            payload["server"] = {"url": server_url}

        if request.dry_run_only or not self._vapi_config_changes_enabled():
            return VoiceProviderActionResponse(
                action="create_phone_number",
                status="skipped",
                dry_run=True,
                request_payload=payload,
            )
        response = self.vapi_client.create_phone_number(payload)
        return VoiceProviderActionResponse(
            action="create_phone_number",
            status="created",
            dry_run=False,
            provider_id=_extract_vapi_id(response),
            request_payload=payload,
            provider_response=response,
        )

    def create_outbound_call(self, request: VoiceOutboundCallRequest) -> VoiceProviderActionResponse:
        assistant_id = request.assistant_id or self.settings.vapi_default_assistant_id
        phone_number_id = request.phone_number_id or self.settings.vapi_default_phone_number_id
        payload: dict[str, Any] = {
            "customer": {"number": normalize_phone_number(request.to)},
            "metadata": {"ares_voice_agent": True, **request.metadata},
        }
        if assistant_id:
            payload["assistantId"] = assistant_id
        else:
            payload["assistant"] = self.build_assistant_payload(
                first_message=request.first_message or "Hi, this is Ares. I’m calling about your property request.",
                system_prompt=request.system_prompt
                or "You are a concise real-estate outbound assistant. Confirm interest and hand off to an operator.",
            )
        if phone_number_id:
            payload["phoneNumberId"] = phone_number_id
        if request.earliest_at:
            payload["schedulePlan"] = {"earliestAt": request.earliest_at}
            if request.latest_at:
                payload["schedulePlan"]["latestAt"] = request.latest_at

        if request.dry_run_only or not self._outbound_calls_enabled():
            return VoiceProviderActionResponse(
                action="create_outbound_call",
                status="skipped",
                dry_run=True,
                request_payload=payload,
            )
        if "phoneNumberId" not in payload:
            raise RuntimeError("VAPI_DEFAULT_PHONE_NUMBER_ID or phone_number_id is required for outbound calls")
        response = self.vapi_client.create_call(payload)
        return VoiceProviderActionResponse(
            action="create_outbound_call",
            status="queued",
            dry_run=False,
            provider_id=_extract_vapi_id(response),
            request_payload=payload,
            provider_response=response,
        )

    def handle_webhook(self, payload: dict[str, Any]) -> VapiWebhookResponse:
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, dict):
            return VapiWebhookResponse(status="accepted", event_type="unknown")
        message_type = str(message.get("type") or "unknown")
        if message_type == "assistant-request":
            if self.settings.vapi_default_assistant_id:
                return VapiWebhookResponse(assistantId=self.settings.vapi_default_assistant_id)
            assistant = self.build_assistant_payload()
            return VapiWebhookResponse(assistant=assistant)
        if message_type == "tool-calls":
            tool_calls = message.get("toolCallList") or message.get("toolCalls") or []
            results: list[dict[str, Any]] = []
            if isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict):
                        continue
                    tool_call_id = str(tool_call.get("id") or tool_call.get("toolCallId") or "")
                    name = str(tool_call.get("name") or tool_call.get("function", {}).get("name") or "unknown")
                    results.append(
                        {
                            "name": name,
                            "toolCallId": tool_call_id,
                            "result": json.dumps({"status": "unsupported", "message": "Tool not wired in Ares yet"}),
                        }
                    )
            return VapiWebhookResponse(results=results)
        return VapiWebhookResponse(status="accepted", event_type=message_type)

    def build_assistant_payload(
        self,
        *,
        name: str = "Ares Voice Agent",
        first_message: str = "Hi, this is Ares. How can I help?",
        system_prompt: str = "You are a concise real-estate phone assistant for Ares. Keep responses under 30 words and hand off when a seller needs an operator.",
        server_url: str | None = None,
        model_provider: str | None = None,
        model: str | None = None,
        voice_provider: str | None = None,
        voice_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "firstMessage": first_message,
            "model": {
                "provider": model_provider or self.settings.vapi_default_model_provider,
                "model": model or self.settings.vapi_default_model,
                "messages": [{"role": "system", "content": system_prompt}],
            },
            "voice": {
                "provider": voice_provider or self.settings.vapi_default_voice_provider,
                "voiceId": voice_id or self.settings.vapi_default_voice_id,
            },
        }
        active_server_url = server_url or self.settings.vapi_webhook_url
        if active_server_url:
            payload["server"] = {"url": active_server_url}
        if metadata:
            payload["metadata"] = metadata
        return payload

    def _vapi_config_changes_enabled(self) -> bool:
        return self.settings.provider_live_sends_enabled and self.settings.vapi_provider_live_sends_enabled

    def _outbound_calls_enabled(self) -> bool:
        return self._vapi_config_changes_enabled()


def _extract_vapi_id(response: dict[str, Any]) -> str | None:
    value = response.get("id") or response.get("assistantId") or response.get("phoneNumberId") or response.get("callId")
    return str(value) if value is not None else None
