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
from app.models.probate_leads import ProbateLeadRecord


class ProbateLeadsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def upsert(self, *, business_id: str, environment: str, record: ProbateLeadRecord) -> ProbateLeadRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(business_id=business_id, environment=environment, record=record)

        lookup_key = (business_id, environment, record.identity_key())
        now = utc_now()
        with self.client.transaction() as store:
            existing_id = store.probate_lead_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.probate_leads[existing_id]
                updates = record.model_dump(exclude={"id", "last_seen_at"})
                if record.last_seen_at is None:
                    updates["last_seen_at"] = existing.last_seen_at
                updated = existing.model_copy(update={**updates, "id": existing_id})
                store.probate_leads[existing_id] = updated
                return updated

            probate_lead_id = record.id or generate_stable_id("prob", business_id, environment, record.identity_key())
            created = record.model_copy(update={"id": probate_lead_id, "last_seen_at": record.last_seen_at or now})
            store.probate_leads[probate_lead_id] = created
            store.probate_lead_keys[lookup_key] = probate_lead_id
            return created

    def get(self, probate_lead_id: str) -> ProbateLeadRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(probate_lead_id, "prob")
            if row_id is None:
                return None
            rows = fetch_rows(
                "probate_leads",
                params={"select": "*", "id": f"eq.{row_id}", "limit": "1"},
                settings=self.settings,
            )
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.probate_leads.get(probate_lead_id)

    def list(self, *, business_id: str | None = None, environment: str | None = None) -> list[ProbateLeadRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            params = {"select": "*", "order": "created_at.asc"}
            if business_id is not None:
                if business_id.isdigit():
                    params["business_id"] = f"eq.{business_id}"
                else:
                    if environment is None:
                        raise ValueError("environment is required when business_id is not numeric")
                    tenant = resolve_tenant(business_id, environment, settings=self.settings)
                    params["business_id"] = f"eq.{tenant.business_pk}"
                    params["environment"] = f"eq.{tenant.environment}"
            elif environment is not None:
                params["environment"] = f"eq.{environment}"
            return [self._record_from_supabase(row) for row in fetch_rows("probate_leads", params=params, settings=self.settings)]

        with self.client.transaction() as store:
            if business_id is None and environment is None:
                records = list(store.probate_leads.values())
            else:
                allowed_ids = {
                    probate_lead_id
                    for (row_business_id, row_environment, _), probate_lead_id in store.probate_lead_keys.items()
                    if (business_id is None or row_business_id == business_id)
                    and (environment is None or row_environment == environment)
                }
                records = [store.probate_leads[record_id] for record_id in allowed_ids]
        records.sort(key=lambda record: (record.case_number, record.id or ""))
        return records

    def _upsert_in_supabase(self, *, business_id: str, environment: str, record: ProbateLeadRecord) -> ProbateLeadRecord:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        payload = record.model_dump(mode="json", exclude={"id"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        rows = fetch_rows(
            "probate_leads",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "source": f"eq.{record.source}",
                "case_number": f"eq.{record.case_number}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if rows:
            row = patch_rows(
                "probate_leads",
                params={"id": f"eq.{rows[0]['id']}"},
                row=payload,
                select="*",
                settings=self.settings,
            )[0]
            return self._record_from_supabase(row)

        row = insert_rows("probate_leads", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict) -> ProbateLeadRecord:
        allowed_fields = set(ProbateLeadRecord.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("prob", row["id"])
        return ProbateLeadRecord.model_validate(payload)
