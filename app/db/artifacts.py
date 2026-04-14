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
        artifact_type: str,
        payload: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        if self._is_supabase():
            supabase = self._supabase_client()
            run_rows = supabase.select(
                "runs",
                columns="id,business_id,environment,runtime_id",
                filters={"runtime_id": run_id},
                limit=1,
            )
            if not run_rows:
                return None

            run_row = run_rows[0]
            artifact_created_at = created_at or utc_now()
            runtime_id = generate_id("art")
            rows = supabase.insert(
                "artifacts",
                rows=[
                    {
                        "runtime_id": runtime_id,
                        "run_runtime_id": run_id,
                        "run_id": run_row["id"],
                        "business_id": run_row["business_id"],
                        "environment": run_row["environment"],
                        "artifact_type": artifact_type,
                        "payload": payload or {},
                        "data": payload or {},
                        "created_at": artifact_created_at.isoformat(),
                    }
                ],
                columns="id,runtime_id,run_runtime_id,artifact_type,payload,data,created_at",
            )
            if not rows:
                return None
            row = rows[0]
            row_payload = row.get("payload")
            if not isinstance(row_payload, dict):
                row_payload = row.get("data") if isinstance(row.get("data"), dict) else {}
            return {
                "id": str(row.get("runtime_id") or row["id"]),
                "run_id": run_id,
                "artifact_type": row["artifact_type"],
                "payload": row_payload,
                "created_at": row["created_at"],
            }

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
        if self._is_supabase():
            rows = self._supabase_client().select(
                "artifacts",
                columns="id,runtime_id,run_runtime_id,artifact_type,payload,data,created_at",
                filters={"run_runtime_id": run_id},
                order="created_at.asc",
            )
            artifacts: list[dict[str, Any]] = []
            for row in rows:
                row_payload = row.get("payload")
                if not isinstance(row_payload, dict):
                    row_payload = row.get("data") if isinstance(row.get("data"), dict) else {}
                artifacts.append(
                    {
                        "id": str(row.get("runtime_id") or row["id"]),
                        "run_id": run_id,
                        "artifact_type": row["artifact_type"],
                        "payload": row_payload,
                        "created_at": row["created_at"],
                    }
                )
            return artifacts

        with self.client.transaction() as store:
            run = store.runs.get(run_id)
            if run is None:
                return []
            return list(run.artifacts)
