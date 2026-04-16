from __future__ import annotations

from collections.abc import Iterable

from app.models.providers import (
    ProviderAuthRecord,
    ProviderCapabilityRecord,
    ProviderKind,
    ProviderRequest,
    ProviderStreamChunk,
)
from app.services.providers.base import BaseRuntimeProvider


class OpenAICompatProvider(BaseRuntimeProvider):
    kind = ProviderKind.OPENAI_COMPAT
    description = "OpenAI-compatible runtime provider"
    default_model = "gpt-4.1"

    @property
    def required_settings(self) -> list[str]:
        return ["openai_compat_api_key", "openai_compat_base_url"]

    def is_configured(self) -> bool:
        return bool(self.settings.openai_compat_api_key and self.settings.openai_compat_base_url and self.transport_configured)

    def auth_record(self) -> ProviderAuthRecord:
        configured_fields = [
            name
            for name, value in (
                ("openai_compat_api_key", self.settings.openai_compat_api_key),
                ("openai_compat_base_url", self.settings.openai_compat_base_url),
            )
            if value
        ]
        missing_fields = [
            name
            for name, value in (
                ("openai_compat_api_key", self.settings.openai_compat_api_key),
                ("openai_compat_base_url", self.settings.openai_compat_base_url),
            )
            if not value
        ]
        state = self._auth_state_from_fields(configured_fields, missing_fields)
        return ProviderAuthRecord(
            state=state,
            configured_fields=configured_fields,
            missing_fields=missing_fields,
            base_url=self.settings.openai_compat_base_url,
            auth_header_name="Authorization",
        )

    @property
    def capabilities(self) -> ProviderCapabilityRecord:
        return ProviderCapabilityRecord(
            streaming=True,
            tool_calls=True,
            json_schema=True,
            long_context=False,
            max_context_tokens=128000,
        )

    def _stream_transport(self, request: ProviderRequest) -> Iterable[ProviderStreamChunk]:
        if self.stream_transport is None:
            raise RuntimeError("OpenAI-compatible provider transport is not configured")
        return self.stream_transport(request)
