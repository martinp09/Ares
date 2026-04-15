from __future__ import annotations

from app.host_adapters.base import HostAdapter
from app.models.host_adapters import (
    HostAdapterDispatchRequest,
    HostAdapterDispatchResult,
    HostAdapterDispatchStatus,
    HostAdapterKind,
)


class CodexHostAdapter(HostAdapter):
    kind = HostAdapterKind.CODEX
    enabled = False
    description = "Reserved adapter seam for a future Codex runtime"

    def dispatch(self, request: HostAdapterDispatchRequest) -> HostAdapterDispatchResult:
        return HostAdapterDispatchResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            status=HostAdapterDispatchStatus.DISABLED,
            message="codex adapter is disabled in this environment",
        )
