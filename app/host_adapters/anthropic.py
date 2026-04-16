from __future__ import annotations

from app.host_adapters.base import HostAdapter
from app.models.host_adapters import (
    HostAdapterDispatchRequest,
    HostAdapterDispatchResult,
    HostAdapterDispatchStatus,
    HostAdapterKind,
)


class AnthropicHostAdapter(HostAdapter):
    kind = HostAdapterKind.ANTHROPIC
    enabled = False
    description = "Reserved adapter seam for a future Anthropic runtime"

    def dispatch(self, request: HostAdapterDispatchRequest) -> HostAdapterDispatchResult:
        return HostAdapterDispatchResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            status=HostAdapterDispatchStatus.DISABLED,
            message="anthropic adapter is disabled in this environment",
        )
