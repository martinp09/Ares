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
from app.models.campaigns import CampaignRecord
from app.models.commands import generate_stable_id


class CampaignsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = False
        self.settings = settings or get_settings()

    def upsert(self, record: CampaignRecord, *, dedupe_key: str | None = None) -> CampaignRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(record, dedupe_key=dedupe_key)
        now = utc_now()
        resolved_key = dedupe_key or record.identity_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.campaign_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.campaigns[existing_id]
                updates = record.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.campaigns[existing_id] = updated
                return updated

            campaign_id = record.id or generate_stable_id("camp", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": campaign_id, "updated_at": now})
            store.campaigns[campaign_id] = created
            store.campaign_keys[lookup_key] = campaign_id
            return created

    def get(self, campaign_id: str) -> CampaignRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(campaign_id, "camp")
            if row_id is None:
                return None
            rows = fetch_rows("campaigns", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.campaigns.get(campaign_id)

    def get_by_key(self, *, business_id: str, environment: str, dedupe_key: str) -> CampaignRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            rows = fetch_rows(
                "campaigns",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "or": f"(provider_name.is.null,name.eq.{dedupe_key.split(':',1)[-1]})",
                    "limit": "1",
                },
                settings=self.settings,
            )
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            campaign_id = store.campaign_keys.get((business_id, environment, dedupe_key))
            if campaign_id is None:
                return None
            return store.campaigns.get(campaign_id)

    def list(self, *, business_id: str | None = None, environment: str | None = None) -> list[CampaignRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            params = {"select": "*", "order": "created_at.asc"}
            if business_id and business_id.isdigit():
                params["business_id"] = f"eq.{business_id}"
            if environment is not None:
                params["environment"] = f"eq.{environment}"
            return [self._record_from_supabase(row) for row in fetch_rows("campaigns", params=params, settings=self.settings)]
        with self.client.transaction() as store:
            records = list(store.campaigns.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        records.sort(key=lambda record: (record.business_id, record.environment, record.name.casefold(), record.created_at))
        return records

    def _upsert_in_supabase(self, record: CampaignRecord, *, dedupe_key: str | None = None) -> CampaignRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        payload = record.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        existing = None
        if record.provider_name and record.provider_campaign_id:
            rows = fetch_rows(
                "campaigns",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "provider_name": f"eq.{record.provider_name}",
                    "provider_campaign_id": f"eq.{record.provider_campaign_id}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            existing = rows[0] if rows else None
        if existing is None:
            rows = fetch_rows(
                "campaigns",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "name": f"eq.{record.name}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            existing = rows[0] if rows else None
        if existing is not None:
            row = patch_rows("campaigns", params={"id": f"eq.{existing['id']}"}, row=payload, select="*", settings=self.settings)[0]
            return self._record_from_supabase(row)
        row = insert_rows("campaigns", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict) -> CampaignRecord:
        payload = dict(row)
        payload["id"] = external_id("camp", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        return CampaignRecord.model_validate(payload)
