from __future__ import annotations

from collections.abc import Sequence

from app.host_adapters.anthropic import AnthropicHostAdapter
from app.host_adapters.base import HostAdapter
from app.host_adapters.codex import CodexHostAdapter
from app.host_adapters.trigger_dev import TriggerDevHostAdapter
from app.models.host_adapters import HostAdapterKind, HostAdapterRecord

DEFAULT_HOST_ADAPTER_KIND = HostAdapterKind.TRIGGER_DEV


class HostAdapterRegistry:
    def __init__(self, adapters: Sequence[HostAdapter] | None = None):
        active_adapters = list(adapters or [TriggerDevHostAdapter(), CodexHostAdapter(), AnthropicHostAdapter()])
        self._adapters = {HostAdapterKind(adapter.kind): adapter for adapter in active_adapters}

    def get_adapter(self, kind: HostAdapterKind | str | None = None) -> HostAdapter:
        resolved_kind = HostAdapterKind(kind or DEFAULT_HOST_ADAPTER_KIND)
        adapter = self._adapters.get(resolved_kind)
        if adapter is None:
            raise ValueError(f"Host adapter '{resolved_kind}' is not registered")
        return adapter

    def list_adapters(self) -> list[HostAdapterRecord]:
        return [self._adapters[kind].describe() for kind in HostAdapterKind if kind in self._adapters]


host_adapter_registry = HostAdapterRegistry()
