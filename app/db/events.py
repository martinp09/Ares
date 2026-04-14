from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.client import (
    ControlPlaneClient,
    SupabaseControlPlaneClient,
    get_control_plane_client,
    register_runtime_sql_identity,
    utc_now,
)
from app.models.commands import generate_id


def event_row_from_record(event: dict[str, Any], *, business_id: int, environment: str) -> dict[str, Any]:
    return {
        "runtime_id": event["id"],
        "run_runtime_id": event["run_id"],
        "business_id": business_id,
        "environment": environment,
        "event_type": event["event_type"],
        "payload": event["payload"],
        "created_at": event["created_at"],
    }


class EventsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def _is_supabase(self) -> bool:
        return getattr(self.client, "backend", None) == "supabase"

    def _supabase_client(self) -> SupabaseControlPlaneClient:
        if not isinstance(self.client, SupabaseControlPlaneClient):
            return self.client  # type: ignore[return-value]
        return self.client

    def append(
        self,
        run_id: str,
        *,
        event_type: str,
        payload: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        if self._is_supabase():
            supabase = self._supabase_client()
            run_rows = supabase.select(
                "runs",
                columns="id,business_id,environment,command_id,command_runtime_id,runtime_id",
                filters={"runtime_id": run_id},
                limit=1,
            )
            if not run_rows:
                return None

            run_row = run_rows[0]
            event_created_at = created_at or utc_now()
            runtime_id = generate_id("evt")
            rows = supabase.insert(
                "events",
                rows=[
                    {
                        "runtime_id": runtime_id,
                        "run_runtime_id": run_id,
                        "run_id": run_row["id"],
                        "command_runtime_id": run_row.get("command_runtime_id"),
                        "command_id": run_row.get("command_id"),
                        "business_id": run_row["business_id"],
                        "environment": run_row["environment"],
                        "event_type": event_type,
                        "payload": payload or {},
                        "created_at": event_created_at.isoformat(),
                    }
                ],
                columns="id,runtime_id,run_runtime_id,event_type,payload,created_at",
            )
            if not rows:
                return None
            row = rows[0]
            return {
                "id": str(row.get("runtime_id") or row["id"]),
                "run_id": run_id,
                "event_type": row["event_type"],
                "payload": row.get("payload", {}) or {},
                "created_at": row["created_at"],
            }

        with self.client.transaction() as store:
            run = store.runs.get(run_id)
            if run is None:
                return None

            event_created_at = created_at or utc_now()
            event = {
                "id": generate_id("evt"),
                "run_id": run_id,
                "event_type": event_type,
                "payload": payload or {},
                "created_at": event_created_at.isoformat(),
            }
            run.events.append(event)
            run.events.sort(key=lambda item: item["created_at"])
            run.updated_at = event_created_at
            store.runs[run_id] = run
            register_runtime_sql_identity(store, table="events", runtime_id=event["id"])
            return event

    def list_for_run(self, run_id: str) -> list[dict[str, Any]]:
        if self._is_supabase():
            rows = self._supabase_client().select(
                "events",
                columns="id,runtime_id,run_runtime_id,event_type,payload,created_at",
                filters={"run_runtime_id": run_id},
                order="created_at.asc",
            )
            return [
                {
                    "id": str(row.get("runtime_id") or row["id"]),
                    "run_id": run_id,
                    "event_type": row["event_type"],
                    "payload": row.get("payload", {}) or {},
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        with self.client.transaction() as store:
            run = store.runs.get(run_id)
            if run is None:
                return []
            return list(run.events)
