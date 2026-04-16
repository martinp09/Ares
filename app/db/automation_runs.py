from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.automation_runs import AutomationRunRecord
from app.models.commands import generate_stable_id


class AutomationRunsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(self, record: AutomationRunRecord, *, dedupe_key: str | None = None) -> AutomationRunRecord:
        now = utc_now()
        resolved_key = dedupe_key or record.replay_safe_key()
        lookup_key = (record.business_id, record.environment, record.workflow_name, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.automation_run_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.automation_runs[existing_id]
                return existing.model_copy(update={"deduped": True})

            run_id = record.id or generate_stable_id(
                "arun",
                record.business_id,
                record.environment,
                record.workflow_name,
                resolved_key,
            )
            created = record.model_copy(update={"id": run_id, "updated_at": now})
            store.automation_runs[run_id] = created
            store.automation_run_keys[lookup_key] = run_id
            return created

    def save(self, record: AutomationRunRecord) -> AutomationRunRecord:
        if record.id is None:
            return self.create(record)
        with self.client.transaction() as store:
            existing = store.automation_runs.get(record.id)
            if existing is None:
                return self.create(record)
            updated = record.model_copy(update={"updated_at": utc_now()})
            store.automation_runs[record.id] = updated
            return updated

    def get(self, run_id: str) -> AutomationRunRecord | None:
        with self.client.transaction() as store:
            return store.automation_runs.get(run_id)

    def list(self, *, business_id: str | None = None, environment: str | None = None) -> list[AutomationRunRecord]:
        with self.client.transaction() as store:
            runs = list(store.automation_runs.values())
        if business_id is not None:
            runs = [run for run in runs if run.business_id == business_id]
        if environment is not None:
            runs = [run for run in runs if run.environment == environment]
        runs.sort(key=lambda run: (run.business_id, run.environment, run.created_at, run.id or ""))
        return runs
