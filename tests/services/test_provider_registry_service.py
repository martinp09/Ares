import pytest

from app.core.config import Settings
from app.models.providers import (
    ProviderKind,
    ProviderRequest,
    ProviderStreamChunk,
    ProviderStreamChunkType,
)
from app.services.provider_registry_service import ProviderRegistryService
from app.services.providers.anthropic import AnthropicProvider
from app.services.providers.local import LocalProvider
from app.services.providers.openai_compat import OpenAICompatProvider


def _done_transport(provider_kind: ProviderKind):
    def _inner(request: ProviderRequest):
        yield ProviderStreamChunk(
            provider_kind=provider_kind,
            chunk_type=ProviderStreamChunkType.DONE,
            done=True,
            raw={"provider": provider_kind.value, "chunk_type": "done", "messages": len(request.messages)},
        )

    return _inner


def test_provider_registry_lists_capabilities_and_resolves_explicit_default() -> None:
    settings = Settings(
        runtime_provider_default="openai_compat",
        anthropic_api_key="anthropic-key",
        openai_compat_api_key="openai-key",
        openai_compat_base_url="https://example.com/v1",
        local_provider_enabled=True,
    )
    registry = ProviderRegistryService(
        settings,
        adapters={
            ProviderKind.ANTHROPIC: AnthropicProvider(settings, stream_transport=_done_transport(ProviderKind.ANTHROPIC)),
            ProviderKind.OPENAI_COMPAT: OpenAICompatProvider(
                settings,
                stream_transport=_done_transport(ProviderKind.OPENAI_COMPAT),
            ),
            ProviderKind.LOCAL: LocalProvider(settings),
        },
    )

    providers = {entry.provider_kind: entry for entry in registry.list_providers()}

    assert registry.resolve_provider_kind() == ProviderKind.OPENAI_COMPAT
    assert registry.get_provider().kind == ProviderKind.OPENAI_COMPAT
    assert providers[ProviderKind.ANTHROPIC].configured is True
    assert providers[ProviderKind.ANTHROPIC].auth.state.value == "configured"
    assert providers[ProviderKind.ANTHROPIC].capabilities.streaming is True
    assert providers[ProviderKind.OPENAI_COMPAT].configured is True
    assert providers[ProviderKind.OPENAI_COMPAT].auth.state.value == "configured"
    assert providers[ProviderKind.OPENAI_COMPAT].default_model == "gpt-4.1"
    assert providers[ProviderKind.LOCAL].enabled is True
    assert providers[ProviderKind.LOCAL].configured is True
    assert providers[ProviderKind.LOCAL].auth.base_url == "local://echo"


def test_provider_registry_rejects_unconfigured_or_disabled_providers() -> None:
    settings = Settings(local_provider_enabled=False)
    registry = ProviderRegistryService(settings)

    with pytest.raises(ValueError, match="anthropic"):
        registry.get_provider(ProviderKind.ANTHROPIC)

    with pytest.raises(ValueError, match="local"):
        registry.get_provider(ProviderKind.LOCAL)
