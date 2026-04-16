from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderPolicyError(ValueError):
    pass


class ProviderPreflightError(ProviderPolicyError):
    pass


class ProviderTransportError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.headers = headers or {}


class ProviderKind(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI_COMPAT = "openai_compat"
    LOCAL = "local"


class ProviderCapability(StrEnum):
    STREAMING = "streaming"
    TOOL_CALLS = "tool_calls"
    JSON_SCHEMA = "json_schema"
    LONG_CONTEXT = "long_context"


class ProviderAuthState(StrEnum):
    CONFIGURED = "configured"
    PARTIAL = "partial"
    MISSING = "missing"


class ProviderMessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ProviderCapabilityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    streaming: bool = True
    tool_calls: bool = True
    json_schema: bool = False
    long_context: bool = False
    max_context_tokens: int | None = None


class ProviderAuthRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: ProviderAuthState
    configured_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    base_url: str | None = None
    auth_header_name: str | None = None


class ProviderMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ProviderMessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class ProviderToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ProviderToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)


class ProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_kind: ProviderKind | None = None
    model: str | None = None
    messages: list[ProviderMessage] = Field(default_factory=list)
    tools: list[ProviderToolDefinition] = Field(default_factory=list)
    stream: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderCallPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeout_seconds: float
    max_attempts: int
    max_context_tokens: int | None = None
    max_tool_schema_bytes: int


class ProviderPreflightRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estimated_input_tokens: int
    tool_schema_bytes: int
    policy: ProviderCallPolicy


class ProviderRetryState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_count: int
    max_attempts: int
    retry_count: int
    retryable: bool
    exhausted: bool
    next_delay_seconds: float | None = None
    last_error: str | None = None


class ProviderStreamChunkType(StrEnum):
    DELTA = "delta"
    TOOL_CALL = "tool_call"
    DONE = "done"


class ProviderStreamChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_kind: ProviderKind
    chunk_type: ProviderStreamChunkType
    content: str | None = None
    tool_call: ProviderToolCall | None = None
    done: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_kind: ProviderKind
    model: str | None = None
    content: str = ""
    tool_calls: list[ProviderToolCall] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class ProviderRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_kind: ProviderKind
    enabled: bool
    configured: bool
    description: str | None = None
    default_model: str | None = None
    capabilities: ProviderCapabilityRecord
    auth: ProviderAuthRecord
