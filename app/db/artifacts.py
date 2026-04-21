from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.control_plane_supabase import (
    control_plane_backend_enabled,
    external_id,
    fetch_rows,
    insert_rows,
    row_id_from_external_id,
)
from app.models.commands import generate_id


class ArtifactsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = client or get_control_plane_client(self.settings)
        self._force_memory = client is not None

    def append(
        self,
        run_id: str,
        *,
        artifact_type: str,
        payload: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._append_in_supabase(
                run_id,
                artifact_type=artifact_type,
                payload=payload,
                created_at=created_at,
            )
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
            return artifact

    def list_for_run(self, run_id: str) -> list[dict[str, Any]]:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(run_id, "run")
            if row_id is None:
                return []
            rows = fetch_rows(
                "artifacts",
                params={"select": "*", "run_id": f"eq.{row_id}", "order": "created_at.asc"},
                settings=self.settings,
            )
            return [self._record_from_supabase(row) for row in rows]
        with self.client.transaction() as store:
            run = store.runs.get(run_id)
            if run is None:
                return []
            return list(run.artifacts)

    def _append_in_supabase(
        self,
        run_id: str,
        *,
        artifact_type: str,
        payload: dict[str, Any] | None,
        created_at: datetime | None,
    ) -> dict[str, Any] | None:
        run_row_id = row_id_from_external_id(run_id, "run")
        if run_row_id is None:
            return None
        run_rows = fetch_rows(
            "runs",
            params={"select": "business_id,environment", "id": f"eq.{run_row_id}", "limit": "1"},
            settings=self.settings,
        )
        if not run_rows:
            return None
        artifact_created_at = created_at or utc_now()
        row = insert_rows(
            "artifacts",
            [
                {
                    "business_id": run_rows[0]["business_id"],
                    "environment": run_rows[0]["environment"],
                    "run_id": run_row_id,
                    "artifact_type": artifact_type,
                    "data": payload or {},
                    "created_at": artifact_created_at.isoformat(),
                }
            ],
            select="*",
            settings=self.settings,
        )[0]
        return self._record_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict) -> dict[str, Any]:
        return {
            "id": external_id("art", row["id"]),
            "run_id": external_id("run", row["run_id"]) if row.get("run_id") is not None else None,
            "artifact_type": row["artifact_type"],
            "payload": dict(row.get("data") or {}),
            "created_at": row["created_at"],
        }
