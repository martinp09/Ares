from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.host_adapters import (
    HostAdapterDispatchRequest,
    HostAdapterDispatchResult,
    HostAdapterKind,
    HostAdapterRecord,
)


class HostAdapter(ABC):
    kind: HostAdapterKind
    enabled: bool = False
    description: str | None = None

    def describe(self) -> HostAdapterRecord:
        return HostAdapterRecord(kind=self.kind, enabled=self.enabled, description=self.description)

    @abstractmethod
    def dispatch(self, request: HostAdapterDispatchRequest) -> HostAdapterDispatchResult:
        raise NotImplementedError
