from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.client import ControlPlaneClient, get_control_plane_client, register_runtime_sql_identity, utc_now
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

    def append(
        self,
        run_id: str,
        *,
        event_type: str,
        payload: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, Any] | None:
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
        with self.client.transaction() as store:
            run = store.runs.get(run_id)
            if run is None:
                return []
            return list(run.events)
