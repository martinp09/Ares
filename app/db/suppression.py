from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_stable_id
from app.models.suppression import SuppressionRecord


class SuppressionRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def upsert(self, record: SuppressionRecord, *, dedupe_key: str | None = None) -> SuppressionRecord:
        now = utc_now()
        resolved_key = dedupe_key or record.scope_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        archived_at = record.archived_at or (now if not record.active else None)
        with self.client.transaction() as store:
            existing_id = store.suppression_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.suppressions[existing_id]
                updates = record.model_dump(exclude={"id", "created_at", "updated_at", "archived_at"})
                updated = existing.model_copy(
                    update={
                        **updates,
                        "updated_at": now,
                        "archived_at": archived_at,
                    }
                )
                store.suppressions[existing_id] = updated
                return updated

            suppression_id = record.id or generate_stable_id(
                "sup",
                record.business_id,
                record.environment,
                resolved_key,
            )
            created = record.model_copy(update={"id": suppression_id, "updated_at": now, "archived_at": archived_at})
            store.suppressions[suppression_id] = created
            store.suppression_keys[lookup_key] = suppression_id
            return created

    def get(self, suppression_id: str) -> SuppressionRecord | None:
        with self.client.transaction() as store:
            return store.suppressions.get(suppression_id)

    def list_active(self, *, business_id: str | None = None, environment: str | None = None) -> list[SuppressionRecord]:
        with self.client.transaction() as store:
            records = [record for record in store.suppressions.values() if record.active]
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        records.sort(key=lambda record: (record.business_id, record.environment, record.created_at, record.id or ""))
        return records
