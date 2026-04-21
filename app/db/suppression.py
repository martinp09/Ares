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
from app.models.commands import generate_stable_id
from app.models.suppression import SuppressionRecord


class SuppressionRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = False
        self.settings = settings or get_settings()

    def upsert(self, record: SuppressionRecord, *, dedupe_key: str | None = None) -> SuppressionRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(record, dedupe_key=dedupe_key)
        now = utc_now()
        resolved_key = dedupe_key or record.scope_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        archived_at = record.archived_at or (now if not record.active else None)
        with self.client.transaction() as store:
            existing_id = store.suppression_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.suppressions[existing_id]
                updates = record.model_dump(exclude={"id", "created_at", "updated_at", "archived_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now, "archived_at": archived_at})
                store.suppressions[existing_id] = updated
                return updated
            suppression_id = record.id or generate_stable_id("sup", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": suppression_id, "updated_at": now, "archived_at": archived_at})
            store.suppressions[suppression_id] = created
            store.suppression_keys[lookup_key] = suppression_id
            return created

    def get(self, suppression_id: str) -> SuppressionRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(suppression_id, "sup")
            if row_id is None:
                return None
            rows = fetch_rows("suppressions", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.suppressions.get(suppression_id)

    def list_active(self, *, business_id: str | None = None, environment: str | None = None) -> list[SuppressionRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            params = {"select": "*", "active": "eq.true", "order": "created_at.asc"}
            if business_id and business_id.isdigit():
                params["business_id"] = f"eq.{business_id}"
            if environment is not None:
                params["environment"] = f"eq.{environment}"
            return [self._record_from_supabase(row) for row in fetch_rows("suppressions", params=params, settings=self.settings)]
        with self.client.transaction() as store:
            records = [record for record in store.suppressions.values() if record.active]
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        records.sort(key=lambda record: (record.business_id, record.environment, record.created_at, record.id or ""))
        return records

    def _upsert_in_supabase(self, record: SuppressionRecord, *, dedupe_key: str | None = None) -> SuppressionRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        resolved_key = dedupe_key or record.scope_key()
        payload = record.model_dump(mode="json", exclude={"id", "business_id", "environment"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["scope_key"] = resolved_key
        payload["lead_id"] = row_id_from_external_id(record.lead_id, "lead")
        payload["campaign_id"] = row_id_from_external_id(record.campaign_id, "camp")
        rows = fetch_rows(
            "suppressions",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "scope_key": f"eq.{resolved_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if rows:
            row = patch_rows("suppressions", params={"id": f"eq.{rows[0]['id']}"}, row=payload, select="*", settings=self.settings)[0]
            return self._record_from_supabase(row)
        row = insert_rows("suppressions", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict) -> SuppressionRecord:
        allowed_fields = set(SuppressionRecord.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("sup", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("lead_id") is not None:
            payload["lead_id"] = external_id("lead", row["lead_id"])
        if row.get("campaign_id") is not None:
            payload["campaign_id"] = external_id("camp", row["campaign_id"])
        return SuppressionRecord.model_validate(payload)
