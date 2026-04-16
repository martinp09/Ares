from __future__ import annotations

from copy import deepcopy

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.host_adapters import HostAdapterDispatchRecord, HostAdapterDispatchStatus, HostAdapterKind


class HostAdapterDispatchesRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        adapter_kind: HostAdapterKind,
        agent_id: str,
        agent_revision_id: str,
        business_id: str,
        environment: str,
        skill_ids: list[str] | None = None,
        host_adapter_config: dict | None = None,
        payload: dict | None = None,
        status: HostAdapterDispatchStatus,
        run_id: str | None = None,
        session_id: str | None = None,
        external_reference: str | None = None,
    ) -> HostAdapterDispatchRecord:
        now = utc_now()
        record = HostAdapterDispatchRecord(
            id=generate_id("had"),
            adapter_kind=adapter_kind,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            business_id=business_id,
            environment=environment,
            skill_ids=list(skill_ids or []),
            host_adapter_config=deepcopy(host_adapter_config or {}),
            payload=deepcopy(payload or {}),
            status=status,
            run_id=run_id,
            session_id=session_id,
            external_reference=external_reference,
            created_at=now,
            updated_at=now,
        )
        with self.client.transaction() as store:
            store.host_adapter_dispatches[record.id] = record
        return record

    def get(self, dispatch_id: str) -> HostAdapterDispatchRecord | None:
        with self.client.transaction() as store:
            return store.host_adapter_dispatches.get(dispatch_id)

    def list(self) -> list[HostAdapterDispatchRecord]:
        with self.client.transaction() as store:
            records = list(store.host_adapter_dispatches.values())
        records.sort(key=lambda record: record.created_at)
        return records
