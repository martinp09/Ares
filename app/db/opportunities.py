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
from app.models.opportunities import OpportunityRecord


class OpportunitiesRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def upsert(self, record: OpportunityRecord, *, dedupe_key: str | None = None) -> OpportunityRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(record)

        now = utc_now()
        resolved_key = dedupe_key or f"{record.source_lane}:{record.identity_key()}"
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            rows: dict[str, OpportunityRecord] = getattr(store, "opportunity_rows", {})
            keys: dict[tuple[str, str, str], str] = getattr(store, "opportunity_keys", {})
            setattr(store, "opportunity_rows", rows)
            setattr(store, "opportunity_keys", keys)

            existing_id = keys.get(lookup_key)
            if existing_id is not None:
                existing = rows[existing_id]
                updates = record.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                rows[existing_id] = updated
                return updated

            opportunity_id = record.id or generate_stable_id("opp", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": opportunity_id, "updated_at": now})
            rows[opportunity_id] = created
            keys[lookup_key] = opportunity_id
            return created

    def get(self, opportunity_id: str) -> OpportunityRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(opportunity_id, "opp")
            if row_id is None:
                return None
            rows = fetch_rows("opportunities", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None

        with self.client.transaction() as store:
            rows: dict[str, OpportunityRecord] = getattr(store, "opportunity_rows", {})
            return rows.get(opportunity_id)

    def list(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[OpportunityRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            params: dict[str, str] = {"select": "*", "order": "created_at.asc"}
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
            return [self._record_from_supabase(row) for row in fetch_rows("opportunities", params=params, settings=self.settings)]

        with self.client.transaction() as store:
            rows: dict[str, OpportunityRecord] = getattr(store, "opportunity_rows", {})
            records = list(rows.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        records.sort(key=lambda record: (record.business_id, record.environment, record.created_at, record.id or ""))
        return records

    def _upsert_in_supabase(self, record: OpportunityRecord) -> OpportunityRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        lead_row_id = row_id_from_external_id(record.lead_id, "lead")
        contact_row_id = row_id_from_external_id(record.contact_id, "ctc")
        payload = record.model_dump(
            mode="json",
            exclude={"id", "business_id", "environment", "created_at", "updated_at"},
        )
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["lead_id"] = lead_row_id
        payload["contact_id"] = contact_row_id

        params = {
            "select": "*",
            "business_id": f"eq.{tenant.business_pk}",
            "environment": f"eq.{tenant.environment}",
            "source_lane": f"eq.{record.source_lane}",
            "limit": "1",
        }
        if lead_row_id is not None:
            params["lead_id"] = f"eq.{lead_row_id}"
        elif contact_row_id is not None:
            params["contact_id"] = f"eq.{contact_row_id}"
        rows = fetch_rows("opportunities", params=params, settings=self.settings)
        if rows:
            row = patch_rows(
                "opportunities",
                params={"id": f"eq.{rows[0]['id']}"},
                row=payload,
                select="*",
                settings=self.settings,
            )[0]
            return self._record_from_supabase(row)

        row = insert_rows("opportunities", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict) -> OpportunityRecord:
        payload = dict(row)
        payload["id"] = external_id("opp", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("lead_id") is not None:
            payload["lead_id"] = external_id("lead", row["lead_id"])
        if row.get("contact_id") is not None:
            payload["contact_id"] = external_id("ctc", row["contact_id"])
        return OpportunityRecord.model_validate(payload)
