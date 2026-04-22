from __future__ import annotations

from app.host_adapters.base import HostAdapter
from app.models.host_adapters import HostAdapterCapabilityRecord, HostAdapterDispatchRequest, HostAdapterDispatchResult, HostAdapterKind


class CodexHostAdapter(HostAdapter):
    kind = HostAdapterKind.CODEX
    enabled = False
    display_name = "Codex"
    description = "Reserved host adapter seam for a future Codex runtime"

    @property
    def capabilities(self) -> HostAdapterCapabilityRecord:
        return HostAdapterCapabilityRecord()

    def dispatch(self, request: HostAdapterDispatchRequest) -> HostAdapterDispatchResult:
        return self.disabled_dispatch(request)
