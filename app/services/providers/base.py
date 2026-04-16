from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Any

from app.core.config import Settings, get_settings
from app.models.providers import (
    ProviderAuthRecord,
    ProviderAuthState,
    ProviderCapability,
    ProviderCapabilityRecord,
    ProviderKind,
    ProviderMessage,
    ProviderMessageRole,
    ProviderRegistryEntry,
    ProviderRequest,
    ProviderResponse,
    ProviderStreamChunk,
    ProviderStreamChunkType,
    ProviderToolCall,
)
from app.services.provider_preflight_service import ProviderPreflightService
from app.services.provider_retry_service import ProviderRetryService

ProviderStreamTransport = Callable[[ProviderRequest], Iterable[ProviderStreamChunk]]


class BaseRuntimeProvider(ABC):
    kind: ProviderKind
    description: str = ""
    default_model: str | None = None

    def __init__(self, settings: Settings | None = None, stream_transport: ProviderStreamTransport | None = None) -> None:
        self.settings = settings or get_settings()
        self.stream_transport = stream_transport
        self.preflight_service = ProviderPreflightService(self.settings)
        self.retry_service = ProviderRetryService(self.settings)

    @property
    def enabled(self) -> bool:
        return True

    @property
    def transport_configured(self) -> bool:
        return self.stream_transport is not None

    @property
    def required_settings(self) -> list[str]:
        return []

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def auth_record(self) -> ProviderAuthRecord:
        raise NotImplementedError

    @property
    def capabilities(self) -> ProviderCapabilityRecord:
        return ProviderCapabilityRecord(streaming=True, tool_calls=True)

    def describe(self) -> ProviderRegistryEntry:
        return ProviderRegistryEntry(
            provider_kind=self.kind,
            enabled=self.enabled,
            configured=self.is_configured(),
            description=self.description or None,
            default_model=self.default_model,
            capabilities=self.capabilities,
            auth=self.auth_record(),
        )

    def stream(self, request: ProviderRequest) -> Iterable[ProviderStreamChunk]:
        prepared_request, _ = self.preflight_service.prepare_request(self, request)
        yield from self._stream_with_retry(prepared_request)

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        prepared_request, _ = self.preflight_service.prepare_request(self, request)
        content_parts: list[str] = []
        tool_calls: list[ProviderToolCall] = []
        raw_chunks: list[dict[str, Any]] = []
        for chunk in self._stream_with_retry(prepared_request):
            raw_chunks.append(chunk.raw)
            if chunk.content:
                content_parts.append(chunk.content)
            if chunk.tool_call is not None:
                tool_calls.append(chunk.tool_call)
            if chunk.done:
                break
        return ProviderResponse(
            provider_kind=self.kind,
            model=prepared_request.model or self.default_model,
            content="".join(content_parts),
            tool_calls=tool_calls,
            metadata=dict(prepared_request.metadata),
            raw={"chunks": raw_chunks},
        )

    def _stream_with_retry(self, request: ProviderRequest) -> Iterable[ProviderStreamChunk]:
        attempt = 0
        while True:
            attempt += 1
            try:
                yield from self._stream_transport(request)
                return
            except Exception as exc:
                retry_state = self.retry_service.evaluate(attempt, exc)
                if not retry_state.retryable or retry_state.exhausted:
                    raise
                if retry_state.next_delay_seconds is not None:
                    self.retry_service.sleep(retry_state.next_delay_seconds)

    @abstractmethod
    def _stream_transport(self, request: ProviderRequest) -> Iterable[ProviderStreamChunk]:
        raise NotImplementedError

    @staticmethod
    def _auth_state_from_fields(configured_fields: list[str], missing_fields: list[str]) -> ProviderAuthState:
        if configured_fields and not missing_fields:
            return ProviderAuthState.CONFIGURED
        if configured_fields:
            return ProviderAuthState.PARTIAL
        return ProviderAuthState.MISSING

    @staticmethod
    def _message_content(messages: list[ProviderMessage]) -> str:
        for message in reversed(messages):
            if message.role == ProviderMessageRole.USER:
                return message.content
        if messages:
            return messages[-1].content
        return ""

    def _default_echo_stream(self, request: ProviderRequest) -> Iterable[ProviderStreamChunk]:
        content = self._message_content(request.messages)
        if content:
            yield ProviderStreamChunk(
                provider_kind=self.kind,
                chunk_type=ProviderStreamChunkType.DELTA,
                content=content,
                raw={"provider": self.kind.value, "chunk_type": "delta"},
            )
        yield ProviderStreamChunk(
            provider_kind=self.kind,
            chunk_type=ProviderStreamChunkType.DONE,
            done=True,
            raw={"provider": self.kind.value, "chunk_type": "done"},
        )
