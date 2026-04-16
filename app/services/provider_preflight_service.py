from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING

from app.core.config import Settings, get_settings
from app.models.providers import (
    ProviderCallPolicy,
    ProviderPreflightError,
    ProviderPreflightRecord,
    ProviderRequest,
)

if TYPE_CHECKING:
    from app.services.providers.base import BaseRuntimeProvider


class ProviderPreflightService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def ensure_provider_ready(self, provider: BaseRuntimeProvider) -> None:
        if not provider.enabled:
            raise ProviderPreflightError(f"Provider '{provider.kind.value}' is disabled")
        if not provider.is_configured():
            raise ProviderPreflightError(f"Provider '{provider.kind.value}' is not configured")

    def prepare_request(
        self,
        provider: BaseRuntimeProvider,
        request: ProviderRequest,
    ) -> tuple[ProviderRequest, ProviderPreflightRecord]:
        self.ensure_provider_ready(provider)
        if request.tools and not provider.capabilities.tool_calls:
            raise ProviderPreflightError(f"Provider '{provider.kind.value}' does not support tool calls")

        tool_schema_bytes = self._tool_schema_bytes(request)
        if tool_schema_bytes > self.settings.provider_tool_schema_max_bytes:
            raise ProviderPreflightError(
                f"Provider request tool schema exceeds {self.settings.provider_tool_schema_max_bytes} bytes"
            )

        estimated_input_tokens = self._estimate_input_tokens(request, tool_schema_bytes)
        max_context_tokens = provider.capabilities.max_context_tokens
        if max_context_tokens is not None and estimated_input_tokens > max_context_tokens:
            raise ProviderPreflightError(
                f"Provider request exceeds context window ({estimated_input_tokens} > {max_context_tokens})"
            )

        policy = ProviderCallPolicy(
            timeout_seconds=self.settings.provider_request_timeout_seconds,
            max_attempts=max(1, self.settings.provider_request_max_retries + 1),
            max_context_tokens=max_context_tokens,
            max_tool_schema_bytes=self.settings.provider_tool_schema_max_bytes,
        )
        preflight = ProviderPreflightRecord(
            estimated_input_tokens=estimated_input_tokens,
            tool_schema_bytes=tool_schema_bytes,
            policy=policy,
        )
        metadata = dict(request.metadata)
        metadata["timeout_seconds"] = policy.timeout_seconds
        metadata["preflight"] = preflight.model_dump(mode="json")
        prepared_request = request.model_copy(
            update={
                "provider_kind": request.provider_kind or provider.kind,
                "model": request.model or provider.default_model,
                "metadata": metadata,
            }
        )
        return prepared_request, preflight

    def _tool_schema_bytes(self, request: ProviderRequest) -> int:
        total = 0
        for tool in request.tools:
            payload = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            total += len(json.dumps(payload, sort_keys=True).encode("utf-8"))
        return total

    def _estimate_input_tokens(self, request: ProviderRequest, tool_schema_bytes: int) -> int:
        message_characters = sum(
            len(message.role.value)
            + len(message.content)
            + len(message.name or "")
            + len(message.tool_call_id or "")
            for message in request.messages
        )
        total_characters = message_characters + tool_schema_bytes
        if total_characters <= 0:
            return 0
        return math.ceil(total_characters / 4)
