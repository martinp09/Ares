from __future__ import annotations

from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.host_adapters.base import HostAdapter
from app.models.host_adapters import (
    HostAdapterDispatchRequest,
    HostAdapterDispatchResult,
    HostAdapterDispatchStatus,
    HostAdapterKind,
)


class TriggerDevHostAdapter(HostAdapter):
    kind = HostAdapterKind.TRIGGER_DEV
    enabled = True
    description = "Default in-memory Trigger.dev adapter seam"

    def __init__(self, dispatches_repository: HostAdapterDispatchesRepository | None = None):
        self.dispatches_repository = dispatches_repository or HostAdapterDispatchesRepository()

    def dispatch(self, request: HostAdapterDispatchRequest) -> HostAdapterDispatchResult:
        external_reference = request.run_id
        record = self.dispatches_repository.create(
            adapter_kind=self.kind,
            agent_id=request.agent_id,
            agent_revision_id=request.agent_revision_id,
            business_id=request.business_id,
            environment=request.environment,
            skill_ids=[skill.id for skill in request.skills],
            host_adapter_config=request.host_adapter_config,
            payload=request.payload,
            status=HostAdapterDispatchStatus.ACCEPTED,
            run_id=request.run_id,
            session_id=request.session_id,
            external_reference=external_reference,
        )
        return HostAdapterDispatchResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            status=HostAdapterDispatchStatus.ACCEPTED,
            dispatch_id=record.id,
            external_reference=external_reference,
        )
