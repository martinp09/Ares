from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.campaigns import CampaignRecord
from app.models.commands import generate_stable_id


class CampaignsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def upsert(self, record: CampaignRecord, *, dedupe_key: str | None = None) -> CampaignRecord:
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
        with self.client.transaction() as store:
            return store.campaigns.get(campaign_id)

    def list(self, *, business_id: str | None = None, environment: str | None = None) -> list[CampaignRecord]:
        with self.client.transaction() as store:
            records = list(store.campaigns.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        records.sort(key=lambda record: (record.business_id, record.environment, record.name.casefold(), record.created_at))
        return records
