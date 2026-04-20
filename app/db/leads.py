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
from app.models.leads import LeadRecord


class LeadsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = False
        self.settings = settings or get_settings()

    def upsert(self, record: LeadRecord, *, dedupe_key: str | None = None) -> LeadRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(record, dedupe_key=dedupe_key)
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
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._get_in_supabase(lead_id)
        with self.client.transaction() as store:
            return store.leads.get(lead_id)

    def get_by_key(self, *, business_id: str, environment: str, dedupe_key: str) -> LeadRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._get_by_key_in_supabase(business_id=business_id, environment=environment, dedupe_key=dedupe_key)
        with self.client.transaction() as store:
            lead_id = store.lead_keys.get((business_id, environment, dedupe_key))
            if lead_id is None:
                return None
            return store.leads.get(lead_id)

    def find_by_email(self, *, business_id: str, environment: str, email: str) -> LeadRecord | None:
        normalized_email = email.strip()
        if not normalized_email:
            return None
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            rows = fetch_rows(
                "leads",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "email": f"eq.{normalized_email}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            for record in store.leads.values():
                if (
                    record.business_id == business_id
                    and record.environment == environment
                    and record.email == normalized_email
                ):
                    return record
        return None

    def list(self, *, business_id: str | None = None, environment: str | None = None) -> list[LeadRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            params = {"select": "*", "order": "created_at.asc"}
            if business_id and business_id.isdigit():
                params["business_id"] = f"eq.{business_id}"
            if environment is not None:
                params["environment"] = f"eq.{environment}"
            return [self._record_from_supabase(row) for row in fetch_rows("leads", params=params, settings=self.settings)]
        with self.client.transaction() as store:
            records = list(store.leads.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        records.sort(key=lambda record: (record.business_id, record.environment, record.created_at, record.id or ""))
        return records

    def _upsert_in_supabase(self, record: LeadRecord, *, dedupe_key: str | None = None) -> LeadRecord:
        resolved_key = dedupe_key or record.identity_key()
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        payload = record.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["identity_key"] = resolved_key
        payload["campaign_id"] = row_id_from_external_id(record.campaign_id, "camp")
        payload["probate_lead_id"] = row_id_from_external_id(record.raw_payload.get("probate_lead_id") if isinstance(record.raw_payload, dict) else None, "prob")
        existing = fetch_rows(
            "leads",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "identity_key": f"eq.{resolved_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if existing:
            row = patch_rows(
                "leads",
                params={"id": f"eq.{existing[0]['id']}"},
                row=payload,
                select="*",
                settings=self.settings,
            )[0]
            return self._record_from_supabase(row)
        row = insert_rows("leads", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    def _get_in_supabase(self, lead_id: str) -> LeadRecord | None:
        row_id = row_id_from_external_id(lead_id, "lead")
        if row_id is None:
            return None
        rows = fetch_rows("leads", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
        return self._record_from_supabase(rows[0]) if rows else None

    def _get_by_key_in_supabase(self, *, business_id: str, environment: str, dedupe_key: str) -> LeadRecord | None:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        rows = fetch_rows(
            "leads",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "identity_key": f"eq.{dedupe_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else None

    @staticmethod
    def _record_from_supabase(row: dict) -> LeadRecord:
        allowed_fields = set(LeadRecord.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("lead", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("campaign_id") is not None:
            payload["campaign_id"] = external_id("camp", row["campaign_id"])
        if row.get("probate_lead_id") is not None:
            payload.setdefault("raw_payload", {})
            payload["raw_payload"] = dict(payload["raw_payload"])
            payload["raw_payload"]["probate_lead_id"] = external_id("prob", row["probate_lead_id"])
        return LeadRecord.model_validate(payload)
