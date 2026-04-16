from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_stable_id
from app.models.leads import LeadRecord


class LeadsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def upsert(self, record: LeadRecord, *, dedupe_key: str | None = None) -> LeadRecord:
        now = utc_now()
        resolved_key = dedupe_key or record.identity_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.lead_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.leads[existing_id]
                updates = record.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.leads[existing_id] = updated
                return updated

            lead_id = record.id or generate_stable_id("lead", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": lead_id, "updated_at": now})
            store.leads[lead_id] = created
            store.lead_keys[lookup_key] = lead_id
            return created

    def get(self, lead_id: str) -> LeadRecord | None:
        with self.client.transaction() as store:
            return store.leads.get(lead_id)

    def get_by_key(self, *, business_id: str, environment: str, dedupe_key: str) -> LeadRecord | None:
        with self.client.transaction() as store:
            lead_id = store.lead_keys.get((business_id, environment, dedupe_key))
            if lead_id is None:
                return None
            return store.leads.get(lead_id)

    def list(self, *, business_id: str | None = None, environment: str | None = None) -> list[LeadRecord]:
        with self.client.transaction() as store:
            records = list(store.leads.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        records.sort(key=lambda record: (record.business_id, record.environment, record.created_at, record.id or ""))
        return records
