from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.lead_machine_supabase import (
    external_id,
    fetch_rows,
    insert_rows,
    lead_machine_backend_enabled,
    patch_rows,
    resolve_tenant,
    row_id_from_external_id,
)
from app.models.automation_runs import AutomationRunRecord
from app.models.commands import generate_stable_id


class AutomationRunsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def create(self, record: AutomationRunRecord) -> AutomationRunRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(record)
        with self.client.transaction() as store:
            lookup_key = (record.business_id, record.environment, record.workflow_name, record.replay_safe_key())
            existing_id = store.automation_run_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.automation_runs[existing_id]
                return existing.model_copy(update={"deduped": True})
            run_id = record.id or generate_stable_id(
                "run",
                record.business_id,
                record.environment,
                record.workflow_name,
                record.replay_safe_key(),
            )
            created = record.model_copy(update={"id": run_id})
            store.automation_runs[run_id] = created
            store.automation_run_keys[lookup_key] = run_id
            return created

    def save(self, record: AutomationRunRecord) -> AutomationRunRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(record)
        with self.client.transaction() as store:
            existing = store.automation_runs.get(record.id)
            if existing is None:
                return self.create(record)
            updated = existing.model_copy(update={**record.model_dump(exclude={"created_at"}), "updated_at": utc_now()})
            store.automation_runs[record.id] = updated
            return updated

    def get(self, run_id: str) -> AutomationRunRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(run_id, "run")
            if row_id is None:
                return None
            rows = fetch_rows("automation_runs", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.automation_runs.get(run_id)

    def list(self, *, business_id: str | None = None, environment: str | None = None) -> list[AutomationRunRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            params = {"select": "*", "order": "created_at.asc"}
            if business_id and business_id.isdigit():
                params["business_id"] = f"eq.{business_id}"
            if environment is not None:
                params["environment"] = f"eq.{environment}"
            return [self._record_from_supabase(row) for row in fetch_rows("automation_runs", params=params, settings=self.settings)]
        with self.client.transaction() as store:
            runs = list(store.automation_runs.values())
        if business_id is not None:
            runs = [run for run in runs if run.business_id == business_id]
        if environment is not None:
            runs = [run for run in runs if run.environment == environment]
        return runs

    def _upsert_in_supabase(self, record: AutomationRunRecord) -> AutomationRunRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        payload = record.model_dump(mode="json", exclude={"id", "business_id", "environment", "deduped"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["lead_id"] = row_id_from_external_id(record.lead_id, "lead")
        payload["campaign_id"] = row_id_from_external_id(record.campaign_id, "camp")
        payload["parent_run_id"] = row_id_from_external_id(record.parent_run_id, "run")
        existing = fetch_rows(
            "automation_runs",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "workflow_name": f"eq.{record.workflow_name}",
                "or": f"(replay_key.eq.{record.replay_safe_key()},and(replay_key.is.null,idempotency_key.eq.{record.replay_safe_key()}))",
                "limit": "1",
            },
            settings=self.settings,
        )
        if existing:
            row = patch_rows("automation_runs", params={"id": f"eq.{existing[0]['id']}"}, row=payload, select="*", settings=self.settings)[0]
            return self._record_from_supabase(row)
        row = insert_rows("automation_runs", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict) -> AutomationRunRecord:
        payload = dict(row)
        payload["id"] = external_id("run", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("lead_id") is not None:
            payload["lead_id"] = external_id("lead", row["lead_id"])
        if row.get("campaign_id") is not None:
            payload["campaign_id"] = external_id("camp", row["campaign_id"])
        if row.get("parent_run_id") is not None:
            payload["parent_run_id"] = external_id("run", row["parent_run_id"])
        return AutomationRunRecord.model_validate(payload)
