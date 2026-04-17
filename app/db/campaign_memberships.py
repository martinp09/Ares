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
from app.models.campaigns import CampaignMembershipRecord
from app.models.commands import generate_stable_id


class CampaignMembershipsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def upsert(self, record: CampaignMembershipRecord) -> CampaignMembershipRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(record)
        now = utc_now()
        lookup_key = (record.business_id, record.environment, record.replay_key())
        with self.client.transaction() as store:
            existing_id = store.campaign_membership_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.campaign_memberships[existing_id]
                updated = existing.model_copy(update={**record.model_dump(exclude={"id"}), "updated_at": now})
                store.campaign_memberships[existing_id] = updated
                return updated
            membership_id = record.id or generate_stable_id("mbr", record.business_id, record.environment, record.replay_key())
            created = record.model_copy(update={"id": membership_id, "last_synced_at": record.last_synced_at or now})
            store.campaign_memberships[membership_id] = created
            store.campaign_membership_keys[lookup_key] = membership_id
            store.campaign_membership_ids_by_campaign.setdefault(record.campaign_id, []).append(membership_id)
            store.campaign_membership_ids_by_lead.setdefault(record.lead_id, []).append(membership_id)
            return created

    def get(self, membership_id: str) -> CampaignMembershipRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(membership_id, "mbr")
            if row_id is None:
                return None
            rows = fetch_rows("campaign_memberships", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.campaign_memberships.get(membership_id)

    def list_for_campaign(self, campaign_id: str) -> list[CampaignMembershipRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(campaign_id, "camp")
            rows = fetch_rows("campaign_memberships", params={"select": "*", "campaign_id": f"eq.{row_id}", "order": "subscribed_at.asc"}, settings=self.settings)
            return [self._record_from_supabase(row) for row in rows]
        with self.client.transaction() as store:
            membership_ids = list(store.campaign_membership_ids_by_campaign.get(campaign_id, []))
            return [store.campaign_memberships[membership_id] for membership_id in membership_ids]

    def list_for_lead(self, lead_id: str) -> list[CampaignMembershipRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(lead_id, "lead")
            rows = fetch_rows("campaign_memberships", params={"select": "*", "lead_id": f"eq.{row_id}", "order": "subscribed_at.asc"}, settings=self.settings)
            return [self._record_from_supabase(row) for row in rows]
        with self.client.transaction() as store:
            membership_ids = list(store.campaign_membership_ids_by_lead.get(lead_id, []))
            return [store.campaign_memberships[membership_id] for membership_id in membership_ids]

    def _upsert_in_supabase(self, record: CampaignMembershipRecord) -> CampaignMembershipRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        payload = record.model_dump(mode="json", exclude={"id", "business_id", "environment"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["lead_id"] = row_id_from_external_id(record.lead_id, "lead")
        payload["campaign_id"] = row_id_from_external_id(record.campaign_id, "camp")
        existing = None
        if record.idempotency_key:
            rows = fetch_rows(
                "campaign_memberships",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "idempotency_key": f"eq.{record.idempotency_key}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            existing = rows[0] if rows else None
        if existing is None:
            rows = fetch_rows(
                "campaign_memberships",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "lead_id": f"eq.{payload['lead_id']}",
                    "campaign_id": f"eq.{payload['campaign_id']}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            existing = rows[0] if rows else None
        if existing:
            row = patch_rows("campaign_memberships", params={"id": f"eq.{existing['id']}"}, row=payload, select="*", settings=self.settings)[0]
            return self._record_from_supabase(row)
        row = insert_rows("campaign_memberships", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict) -> CampaignMembershipRecord:
        allowed_fields = set(CampaignMembershipRecord.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("mbr", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        payload["lead_id"] = external_id("lead", row["lead_id"])
        payload["campaign_id"] = external_id("camp", row["campaign_id"])
        return CampaignMembershipRecord.model_validate(payload)
