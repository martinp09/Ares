from app.core.config import Settings
from app.models.providers import (
    ProviderKind,
    ProviderMessage,
    ProviderMessageRole,
    ProviderRequest,
    ProviderStreamChunk,
    ProviderStreamChunkType,
)
from app.services.providers.anthropic import AnthropicProvider
from app.services.providers.local import LocalProvider
from app.services.providers.openai_compat import OpenAICompatProvider


def _transport(provider_kind: ProviderKind):
    def _inner(request: ProviderRequest):
        yield ProviderStreamChunk(
            provider_kind=provider_kind,
            chunk_type=ProviderStreamChunkType.DELTA,
            content=f"{provider_kind.value}:{request.messages[-1].content}",
            raw={"provider": provider_kind.value, "chunk_type": "delta"},
        )
        yield ProviderStreamChunk(
            provider_kind=provider_kind,
            chunk_type=ProviderStreamChunkType.DONE,
            done=True,
            raw={"provider": provider_kind.value, "chunk_type": "done"},
        )

    return _inner


def test_anthropic_and_openai_compat_stream_through_the_same_interface() -> None:
    request = ProviderRequest(
        model="test-model",
        messages=[ProviderMessage(role=ProviderMessageRole.USER, content="hello world")],
        metadata={"turn_id": "trn_123"},
    )

    anthropic = AnthropicProvider(
        Settings(anthropic_api_key="anthropic-key"),
        stream_transport=_transport(ProviderKind.ANTHROPIC),
    )
    openai = OpenAICompatProvider(
        Settings(openai_compat_api_key="openai-key", openai_compat_base_url="https://example.com/v1"),
        stream_transport=_transport(ProviderKind.OPENAI_COMPAT),
    )

    anthropic_chunks = list(anthropic.stream(request))
    openai_chunks = list(openai.stream(request))

    assert anthropic_chunks[0].content == "anthropic:hello world"
    assert openai_chunks[0].content == "openai_compat:hello world"
    assert anthropic.complete(request).content == "anthropic:hello world"
    assert openai.complete(request).content == "openai_compat:hello world"


def test_local_provider_echoes_last_user_message_without_transport() -> None:
    provider = LocalProvider(Settings(local_provider_enabled=True))
    request = ProviderRequest(
        messages=[
            ProviderMessage(role=ProviderMessageRole.SYSTEM, content="stay focused"),
            ProviderMessage(role=ProviderMessageRole.USER, content="echo this back"),
        ]
    )

    response = provider.complete(request)

    assert response.provider_kind == ProviderKind.LOCAL
    assert response.content == "echo this back"
