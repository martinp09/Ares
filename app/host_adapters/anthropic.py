from __future__ import annotations

from app.host_adapters.base import HostAdapter
from app.models.host_adapters import HostAdapterCapabilityRecord, HostAdapterDispatchRequest, HostAdapterDispatchResult, HostAdapterKind


class AnthropicHostAdapter(HostAdapter):
    kind = HostAdapterKind.ANTHROPIC
    enabled = False
    display_name = "Anthropic"
    description = "Reserved host adapter seam for a future Anthropic runtime"

    @property
    def capabilities(self) -> HostAdapterCapabilityRecord:
        return HostAdapterCapabilityRecord()

    def dispatch(self, request: HostAdapterDispatchRequest) -> HostAdapterDispatchResult:
        return self.disabled_dispatch(request)
