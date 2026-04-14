from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.client import ControlPlaneClient, get_control_plane_client, register_runtime_sql_identity, utc_now
from app.models.commands import generate_id


def artifact_row_from_record(artifact: dict[str, Any], *, business_id: int, environment: str) -> dict[str, Any]:
    return {
        "runtime_id": artifact["id"],
        "run_runtime_id": artifact["run_id"],
        "business_id": business_id,
        "environment": environment,
        "artifact_type": artifact["artifact_type"],
        "payload": artifact["payload"],
        "data": artifact["payload"],
        "created_at": artifact["created_at"],
    }


class ArtifactsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def append(
        self,
        run_id: str,
        *,
        artifact_type: str,
        payload: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        with self.client.transaction() as store:
            run = store.runs.get(run_id)
            if run is None:
                return None

            artifact_created_at = created_at or utc_now()
            artifact = {
                "id": generate_id("art"),
                "run_id": run_id,
                "artifact_type": artifact_type,
                "payload": payload or {},
                "created_at": artifact_created_at.isoformat(),
            }
            run.artifacts.append(artifact)
            run.updated_at = artifact_created_at
            store.runs[run_id] = run
            register_runtime_sql_identity(store, table="artifacts", runtime_id=artifact["id"])
            return artifact

    def list_for_run(self, run_id: str) -> list[dict[str, Any]]:
        with self.client.transaction() as store:
            run = store.runs.get(run_id)
            if run is None:
                return []
            return list(run.artifacts)
