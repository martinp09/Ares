from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.permissions import PermissionRecord, ToolPermissionMode


class PermissionsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def upsert(self, *, agent_revision_id: str, tool_name: str, mode: ToolPermissionMode) -> PermissionRecord:
        now = utc_now()
        lookup_key = (agent_revision_id, tool_name)
        with self.client.transaction() as store:
            existing_id = store.permission_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.permissions[existing_id]
                updated = existing.model_copy(update={"mode": mode, "updated_at": now})
                store.permissions[existing_id] = updated
                return updated

            record = PermissionRecord(
                id=generate_id("perm"),
                agent_revision_id=agent_revision_id,
                tool_name=tool_name,
                mode=mode,
                created_at=now,
                updated_at=now,
            )
            store.permissions[record.id] = record
            store.permission_keys[lookup_key] = record.id
            return record

    def get(self, *, agent_revision_id: str, tool_name: str) -> PermissionRecord | None:
        with self.client.transaction() as store:
            existing_id = store.permission_keys.get((agent_revision_id, tool_name))
            if existing_id is None:
                return None
            return store.permissions.get(existing_id)

    def list_for_revision(self, agent_revision_id: str) -> list[PermissionRecord]:
        with self.client.transaction() as store:
            records = [record for record in store.permissions.values() if record.agent_revision_id == agent_revision_id]
        records.sort(key=lambda record: record.tool_name)
        return records
