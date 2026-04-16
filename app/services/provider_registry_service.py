from __future__ import annotations

from collections.abc import Iterable

from app.core.config import Settings, get_settings
from app.models.providers import ProviderKind, ProviderRegistryEntry
from app.services.providers.anthropic import AnthropicProvider
from app.services.providers.base import BaseRuntimeProvider
from app.services.providers.local import LocalProvider
from app.services.providers.openai_compat import OpenAICompatProvider


class ProviderRegistryService:
    def __init__(
        self,
        settings: Settings | None = None,
        adapters: dict[ProviderKind, BaseRuntimeProvider] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._adapters = adapters or self._build_default_adapters()

    def _build_default_adapters(self) -> dict[ProviderKind, BaseRuntimeProvider]:
        return {
            ProviderKind.ANTHROPIC: AnthropicProvider(self.settings),
            ProviderKind.OPENAI_COMPAT: OpenAICompatProvider(self.settings),
            ProviderKind.LOCAL: LocalProvider(self.settings),
        }

    def list_providers(self) -> list[ProviderRegistryEntry]:
        return [adapter.describe() for adapter in self._ordered_adapters()]

    def get_provider(
        self,
        provider_kind: ProviderKind | str | None = None,
        *,
        provider_config: dict[str, object] | None = None,
    ) -> BaseRuntimeProvider:
        resolved_kind = self.resolve_provider_kind(provider_kind)
        adapter = self._adapters.get(resolved_kind)
        if adapter is None:
            raise ValueError(f"Provider '{resolved_kind}' is not registered")
        effective_adapter = adapter
        if provider_config:
            effective_settings = self.settings.model_copy(update=provider_config)
            effective_adapter = adapter.__class__(effective_settings, stream_transport=adapter.stream_transport)
        if not effective_adapter.enabled:
            raise ValueError(f"Provider '{resolved_kind}' is disabled")
        if not effective_adapter.is_configured():
            raise ValueError(f"Provider '{resolved_kind}' is not configured")
        return effective_adapter

    def resolve_provider_kind(self, provider_kind: ProviderKind | str | None = None) -> ProviderKind:
        if provider_kind is not None:
            return ProviderKind(provider_kind)
        return ProviderKind(self.settings.runtime_provider_default)

    def describe_provider(self, provider_kind: ProviderKind | str) -> ProviderRegistryEntry:
        adapter = self._adapters[ProviderKind(provider_kind)]
        return adapter.describe()

    def get_provider_for_revision(self, revision) -> BaseRuntimeProvider:
        return self.get_provider(revision.provider_kind, provider_config=revision.provider_config)

    def _ordered_adapters(self) -> Iterable[BaseRuntimeProvider]:
        for provider_kind in (ProviderKind.ANTHROPIC, ProviderKind.OPENAI_COMPAT, ProviderKind.LOCAL):
            adapter = self._adapters.get(provider_kind)
            if adapter is not None:
                yield adapter


provider_registry_service = ProviderRegistryService()
