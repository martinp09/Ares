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


class LocalProvider(BaseRuntimeProvider):
    kind = ProviderKind.LOCAL
    description = "Local deterministic provider"
    default_model = "local-echo"

    @property
    def required_settings(self) -> list[str]:
        return []

    @property
    def enabled(self) -> bool:
        return self.settings.local_provider_enabled

    def is_configured(self) -> bool:
        return bool(self.settings.local_provider_enabled)

    def auth_record(self) -> ProviderAuthRecord:
        state = ProviderAuthState.CONFIGURED if self.settings.local_provider_enabled else ProviderAuthState.MISSING
        return ProviderAuthRecord(
            state=state,
            configured_fields=["local_provider_enabled"] if self.settings.local_provider_enabled else [],
            missing_fields=[] if self.settings.local_provider_enabled else ["local_provider_enabled"],
            base_url="local://echo",
            auth_header_name=None,
        )

    @property
    def capabilities(self) -> ProviderCapabilityRecord:
        return ProviderCapabilityRecord(
            streaming=True,
            tool_calls=True,
            json_schema=False,
            long_context=False,
            max_context_tokens=32000,
        )

    def _stream_transport(self, request: ProviderRequest) -> Iterable[ProviderStreamChunk]:
        if self.stream_transport is not None:
            return self.stream_transport(request)
        return self._default_echo_stream(request)
