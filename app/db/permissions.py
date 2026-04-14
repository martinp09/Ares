from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.db.client import ControlPlaneClient, SupabaseControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.permissions import PermissionRecord, ToolPermissionMode


def permission_record_from_row(row: Mapping[str, Any]) -> PermissionRecord:
    return PermissionRecord(
        id=str(row.get("runtime_id") or row["id"]),
        agent_revision_id=str(row["agent_revision_id"]),
        tool_name=str(row["tool_name"]),
        mode=ToolPermissionMode(str(row["mode"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PermissionsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def _is_supabase(self) -> bool:
        return getattr(self.client, "backend", None) == "supabase"

    def _supabase_client(self) -> SupabaseControlPlaneClient:
        if not isinstance(self.client, SupabaseControlPlaneClient):
            return self.client  # type: ignore[return-value]
        return self.client

    def _select_supabase_permission(
        self,
        *,
        runtime_id: str | None = None,
        agent_revision_id: str | None = None,
        tool_name: str | None = None,
    ) -> PermissionRecord | None:
        filters: dict[str, str] = {}
        if runtime_id is not None:
            filters["runtime_id"] = runtime_id
        if agent_revision_id is not None:
            filters["agent_revision_id"] = agent_revision_id
        if tool_name is not None:
            filters["tool_name"] = tool_name
        rows = self._supabase_client().select(
            "agent_tool_permissions",
            columns="id,runtime_id,agent_revision_id,tool_name,mode,created_at,updated_at",
            filters=filters,
            limit=1,
        )
        if not rows:
            return None
        return permission_record_from_row(rows[0])

    def upsert(self, *, agent_revision_id: str, tool_name: str, mode: ToolPermissionMode) -> PermissionRecord:
        now = utc_now()
        if self._is_supabase():
            existing = self._select_supabase_permission(agent_revision_id=agent_revision_id, tool_name=tool_name)
            if existing is not None:
                rows = self._supabase_client().update(
                    "agent_tool_permissions",
                    values={
                        "mode": mode.value,
                        "updated_at": now.isoformat(),
                    },
                    filters={"runtime_id": existing.id},
                    columns="id,runtime_id,agent_revision_id,tool_name,mode,created_at,updated_at",
                )
                if not rows:
                    raise RuntimeError(f"Supabase permission update failed for runtime_id '{existing.id}'")
                return permission_record_from_row(rows[0])

            created = PermissionRecord(
                id=generate_id("perm"),
                agent_revision_id=agent_revision_id,
                tool_name=tool_name,
                mode=mode,
                created_at=now,
                updated_at=now,
            )
            rows = self._supabase_client().insert(
                "agent_tool_permissions",
                rows=[
                    {
                        "runtime_id": created.id,
                        "agent_revision_id": agent_revision_id,
                        "tool_name": tool_name,
                        "mode": mode.value,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    }
                ],
                columns="id,runtime_id,agent_revision_id,tool_name,mode,created_at,updated_at",
            )
            if not rows:
                raise RuntimeError("Supabase permission insert failed without returning a row")
            return permission_record_from_row(rows[0])

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
        if self._is_supabase():
            return self._select_supabase_permission(agent_revision_id=agent_revision_id, tool_name=tool_name)
        with self.client.transaction() as store:
            existing_id = store.permission_keys.get((agent_revision_id, tool_name))
            if existing_id is None:
                return None
            return store.permissions.get(existing_id)

    def list_for_revision(self, agent_revision_id: str) -> list[PermissionRecord]:
        if self._is_supabase():
            rows = self._supabase_client().select(
                "agent_tool_permissions",
                columns="id,runtime_id,agent_revision_id,tool_name,mode,created_at,updated_at",
                filters={"agent_revision_id": agent_revision_id},
                order="tool_name.asc",
            )
            return [permission_record_from_row(row) for row in rows]

        with self.client.transaction() as store:
            records = [record for record in store.permissions.values() if record.agent_revision_id == agent_revision_id]
        records.sort(key=lambda record: record.tool_name)
        return records
