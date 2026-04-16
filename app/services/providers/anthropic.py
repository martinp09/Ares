from __future__ import annotations

from collections.abc import Iterable

from app.models.providers import (
    ProviderAuthRecord,
    ProviderAuthState,
    ProviderCapabilityRecord,
    ProviderKind,
    ProviderRequest,
    ProviderStreamChunk,
)
from app.services.providers.base import BaseRuntimeProvider


class AnthropicProvider(BaseRuntimeProvider):
    kind = ProviderKind.ANTHROPIC
    description = "Anthropic runtime provider"
    default_model = "claude-3-5-sonnet-latest"

    @property
    def required_settings(self) -> list[str]:
        return ["anthropic_api_key"]

    def is_configured(self) -> bool:
        return bool(self.settings.anthropic_api_key and self.transport_configured)

    def auth_record(self) -> ProviderAuthRecord:
        configured_fields = ["anthropic_api_key"] if self.settings.anthropic_api_key else []
        missing_fields = ["anthropic_api_key"] if not self.settings.anthropic_api_key else []
        state = self._auth_state_from_fields(configured_fields, missing_fields)
        return ProviderAuthRecord(
            state=state,
            configured_fields=configured_fields,
            missing_fields=missing_fields,
            base_url=self.settings.anthropic_base_url,
            auth_header_name="Authorization",
        )

    @property
    def capabilities(self) -> ProviderCapabilityRecord:
        return ProviderCapabilityRecord(
            streaming=True,
            tool_calls=True,
            json_schema=True,
            long_context=True,
            max_context_tokens=200000,
        )

    def _stream_transport(self, request: ProviderRequest) -> Iterable[ProviderStreamChunk]:
        if self.stream_transport is None:
            raise RuntimeError("Anthropic provider transport is not configured")
        return self.stream_transport(request)
