import pytest

from app.core.config import Settings
from app.models.providers import (
    ProviderCapability,
    ProviderKind,
    ProviderMessage,
    ProviderMessageRole,
    ProviderPreflightError,
    ProviderRequest,
    ProviderStreamChunk,
    ProviderStreamChunkType,
    ProviderTransportError,
)
from app.services.providers.anthropic import AnthropicProvider
from app.services.providers.openai_compat import OpenAICompatProvider


def test_provider_complete_retries_transient_transport_errors_and_records_preflight_metadata() -> None:
    attempts: list[int] = []

    def transport(request: ProviderRequest):
        attempts.append(1)
        if len(attempts) == 1:
            raise ProviderTransportError("rate limited", status_code=429)
        yield ProviderStreamChunk(
            provider_kind=ProviderKind.ANTHROPIC,
            chunk_type=ProviderStreamChunkType.DELTA,
            content="recovered",
            raw={"attempt": len(attempts), "chunk_type": "delta"},
        )
        yield ProviderStreamChunk(
            provider_kind=ProviderKind.ANTHROPIC,
            chunk_type=ProviderStreamChunkType.DONE,
            done=True,
            raw={"attempt": len(attempts), "chunk_type": "done"},
        )

    provider = AnthropicProvider(Settings(anthropic_api_key="anthropic-key"), stream_transport=transport)
    request = ProviderRequest(
        model="test-model",
        messages=[ProviderMessage(role=ProviderMessageRole.USER, content="hello provider")],
        tools=[],
        metadata={"turn_id": "turn_123"},
    )

    response = provider.complete(request)

    assert attempts == [1, 1]
    assert response.content == "recovered"
    assert response.metadata["timeout_seconds"] == 10.0
    assert response.metadata["preflight"]["policy"]["max_attempts"] == 3
    assert response.metadata["preflight"]["estimated_input_tokens"] > 0


def test_provider_stream_fails_preflight_before_transport_when_required_config_is_missing() -> None:
    attempts: list[int] = []

    def transport(request: ProviderRequest):
        attempts.append(1)
        yield ProviderStreamChunk(
            provider_kind=ProviderKind.OPENAI_COMPAT,
            chunk_type=ProviderStreamChunkType.DONE,
            done=True,
            raw={"chunk_type": "done"},
        )

    provider = OpenAICompatProvider(
        Settings(openai_compat_api_key="openai-key"),
        stream_transport=transport,
    )
    request = ProviderRequest(
        messages=[ProviderMessage(role=ProviderMessageRole.USER, content="hello")],
    )

    with pytest.raises(ProviderPreflightError):
        list(provider.stream(request))

    assert attempts == []
